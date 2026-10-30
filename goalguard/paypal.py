"""Sandbox-only PayPal adapter. Requires genuine buyer approval at checkout.

No token vaulting, marketplace routing, automatic renewals, or live endpoint.
"""

import base64
from decimal import Decimal
import json
import threading
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import uuid

from .ledger import Cart, Rejection


class PaymentUnavailable(Exception):
    pass


def usd(cents: int) -> str:
    return format(Decimal(cents) / 100, ".2f")


def money_matches(value: dict, cents: int) -> bool:
    try:
        return value["currency_code"] == "USD" and Decimal(value["value"]) == Decimal(cents) / 100
    except (KeyError, ValueError, TypeError, ArithmeticError):
        return False


class PayPal:
    base_url = "https://api-m.sandbox.paypal.com"

    def __init__(self, client_id: str, client_secret: str, merchant_id: str,
                 return_url: str, cancel_url: str):
        if not all((client_id, client_secret, merchant_id, return_url, cancel_url)):
            raise PaymentUnavailable("Sandbox credentials, merchant ID, return URL and cancel URL are required.")
        self.client_id = client_id
        self.client_secret = client_secret
        self.merchant_id = merchant_id
        self.return_url = return_url
        self.cancel_url = cancel_url
        self._token = None
        self._token_until: float = 0
        self._token_lock = threading.Lock()

    @staticmethod
    def _send(method, url, headers, body=None):
        request = Request(url, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=20) as response:
                raw = response.read()
                return json.loads(raw) if raw else {}
        except HTTPError as error:
            # Do not log headers, credentials or full response bodies.
            raise PaymentUnavailable(f"PayPal returned HTTP {error.code}; reconcile payment status.") from None
        except (URLError, TimeoutError, OSError, ValueError):
            raise PaymentUnavailable("PayPal outcome unavailable; retain the budget commitment.") from None

    def _access_token(self):
        with self._token_lock:
            if self._token and time.time() < self._token_until:
                return self._token
            basic = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
            response = self._send("POST", self.base_url + "/v1/oauth2/token",
                                  {"Authorization": "Basic " + basic,
                                   "Content-Type": "application/x-www-form-urlencoded"},
                                  b"grant_type=client_credentials")
            self._token = response["access_token"]
            self._token_until = time.time() + max(0, int(response["expires_in"]) - 60)
            return self._token

    def _request(self, method, path, body=None, request_id=None):
        headers = {"Authorization": "Bearer " + self._access_token(),
                   "Content-Type": "application/json", "Prefer": "return=representation"}
        if request_id:
            headers["PayPal-Request-Id"] = request_id
        return self._send(method, self.base_url + path, headers,
                          json.dumps(body).encode() if body is not None else None)

    def create_order(self, purchase: dict, cart: Cart):
        subtotal = sum(i.quantity * i.unit_cents for i in cart.items)
        body = {
            "intent": "AUTHORIZE",
            "purchase_units": [{
                "reference_id": purchase["id"], "custom_id": purchase["id"],
                "payee": {"merchant_id": self.merchant_id},
                "items": [{"name": i.sku, "sku": i.sku, "quantity": str(i.quantity),
                           "unit_amount": {"currency_code": "USD", "value": usd(i.unit_cents)}}
                          for i in cart.items],
                "amount": {"currency_code": "USD", "value": usd(cart.total_cents),
                           "breakdown": {
                               "item_total": {"currency_code": "USD", "value": usd(subtotal)},
                               "shipping": {"currency_code": "USD", "value": usd(cart.shipping_cents)},
                               "tax_total": {"currency_code": "USD", "value": usd(cart.tax_cents)},
                           }},
            }],
            "payment_source": {"paypal": {"experience_context": {
                "return_url": self.return_url, "cancel_url": self.cancel_url,
                "shipping_preference": "NO_SHIPPING", "user_action": "PAY_NOW",
            }}},
        }
        request_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "goalguard:create:" + purchase["id"]))
        response = self._request("POST", "/v2/checkout/orders", body, request_id)
        approval_url = next((link["href"] for link in response.get("links", [])
                             if link.get("rel") in ("approve", "payer-action")), None)
        if not response.get("id") or not approval_url:
            raise PaymentUnavailable("PayPal did not return a buyer approval link.")
        return {"order_id": response["id"], "approval_url": approval_url,
                "sandbox": True, "fulfilment": "manual_demo_action"}

    def get_order(self, order_id):
        return self._request("GET", "/v2/checkout/orders/" + order_id)

    def validate_order(self, order: dict, purchase: dict, cart: Cart):
        try:
            units = order["purchase_units"]
            if len(units) != 1:
                raise ValueError()
            unit = units[0]
            matches = (order["id"] == purchase["order_id"]
                       and order["intent"] == "AUTHORIZE"
                       and unit["custom_id"] == purchase["id"]
                       and unit["payee"]["merchant_id"] == self.merchant_id
                       and money_matches(unit["amount"], cart.total_cents))
            items = sorted(unit["items"], key=lambda item: item["sku"])
            wanted = sorted(cart.items, key=lambda item: item.sku)
            if len(items) != len(wanted):
                matches = False
            else:
                matches = matches and all(
                    actual["sku"] == expected.sku
                    and int(actual["quantity"]) == expected.quantity
                    and money_matches(actual["unit_amount"], expected.unit_cents)
                    for actual, expected in zip(items, wanted))
            breakdown = unit["amount"]["breakdown"]
            matches = (matches and money_matches(breakdown["shipping"], cart.shipping_cents)
                       and money_matches(breakdown["tax_total"], cart.tax_cents))
            if not matches:
                raise ValueError()
        except (KeyError, ValueError, TypeError):
            raise Rejection("paypal_order_changed", "PayPal order no longer matches the approved purchase.") from None

    def authorize(self, order_id, request_id):
        return self._request("POST", f"/v2/checkout/orders/{order_id}/authorize", {}, request_id)

    def capture(self, authorization_id, amount_cents, request_id):
        return self._request("POST", f"/v2/payments/authorizations/{authorization_id}/capture",
                             {"amount": {"currency_code": "USD", "value": usd(amount_cents)},
                              "final_capture": True}, request_id)

    def void(self, authorization_id, request_id):
        return self._request("POST", f"/v2/payments/authorizations/{authorization_id}/void", {}, request_id)

    def get_authorization(self, authorization_id):
        return self._request("GET", f"/v2/payments/authorizations/{authorization_id}")
