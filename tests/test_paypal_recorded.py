"""Offline replay of sanitized responses observed in PayPal sandbox on 2026-10-17.

These regressions make no provider requests; provenance is in docs/sandbox-results.json.
"""

from copy import deepcopy
import json
from pathlib import Path
import unittest

from goalguard.ledger import Cart, Item
from goalguard.paypal import PayPal


FIXTURES = Path(__file__).parent / "fixtures" / "paypal-sandbox"


class RecordedPayPal(PayPal):
    def __init__(self, records, merchant="recorded-merchant"):
        super().__init__("offline-id", "offline-secret", merchant,
                         "http://localhost/return", "http://localhost/cancel")
        self.records = iter(records)
        self.calls = 0

    def _access_token(self):
        return "offline-placeholder"

    def _send(self, method, url, headers, body=None):
        record = next(self.records)
        actual_body = json.loads(body) if body is not None else None
        assert method == record["method"]
        assert url == self.base_url + record["path"]
        assert actual_body == record["request"]
        assert headers.get("PayPal-Request-Id") == record["request_id"]
        self.calls += 1
        return deepcopy(record["response"])


class RecordedPayPalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = [json.loads(p.read_text()) for p in sorted(FIXTURES.glob("*.json"))]
        if not cls.records:
            raise AssertionError("Recorded sandbox fixtures are required.")

    def select(self, method, suffix, status=None):
        return [r for r in self.records
                if r["method"] == method and r["path"].endswith(suffix)
                and (status is None or r["response"].get("status") == status)]

    def test_recorded_approved_order_validates_exact_cart(self):
        record = next(r for r in self.records
                      if r["method"] == "GET" and r["response"].get("status") == "APPROVED")
        order = record["response"]
        unit = order["purchase_units"][0]
        adapter = RecordedPayPal([record], unit["payee"]["merchant_id"])
        observed = adapter.get_order(order["id"])
        adapter.validate_order(observed, {"id": unit["custom_id"], "order_id": order["id"]},
                               Cart("demo-merchant", (Item("sandbox-unit", 1, 100),)))
        self.assertEqual(adapter.calls, 1)

    def test_recorded_completed_order_is_authorized_not_captured(self):
        record = self.select("POST", "/authorize")[0]
        adapter = RecordedPayPal([record])
        order_id = record["path"].split("/")[-2]
        order = adapter.authorize(order_id, record["request_id"])
        self.assertEqual(record["http_status"], 201)
        self.assertEqual(order["status"], "COMPLETED")
        payments = order["purchase_units"][0]["payments"]
        self.assertEqual(payments["authorizations"][0]["status"], "CREATED")
        self.assertEqual(payments["authorizations"][0]["amount"],
                         {"currency_code": "USD", "value": "1.00"})
        self.assertFalse(payments.get("captures"))

    def test_recorded_same_key_capture_replay_preserves_resource(self):
        first, replay = self.select("POST", "/capture")
        self.assertEqual([first["http_status"], replay["http_status"]], [201, 200])
        self.assertEqual(first["request_id"], replay["request_id"])
        self.assertEqual(first["request"], replay["request"])
        adapter = RecordedPayPal([first, replay])
        auth_id = first["path"].split("/")[-2]
        captured = adapter.capture(auth_id, 100, first["request_id"])
        retried = adapter.capture(auth_id, 100, first["request_id"])
        self.assertEqual(captured["id"], retried["id"])
        self.assertEqual(retried["status"], "COMPLETED")
        self.assertEqual(retried["amount"], {"currency_code": "USD", "value": "1.00"})

    def test_recorded_void_representation_and_status_refresh(self):
        void = self.select("POST", "/void")[0]
        status = next(r for r in self.records
                      if r["method"] == "GET" and r["response"].get("status") == "VOIDED")
        adapter = RecordedPayPal([void, status])
        auth_id = void["path"].split("/")[-2]
        response = adapter.void(auth_id, void["request_id"])
        self.assertEqual(void["http_status"], 200)
        self.assertEqual(response["status"], "VOIDED")
        self.assertEqual(adapter.get_authorization(auth_id)["status"], "VOIDED")
        self.assertEqual(adapter.calls, 2)
