"""Agent-neutral API logic; actor scope is supplied by trusted authentication."""

from dataclasses import dataclass
from typing import cast

from .catalog import Catalog, stored_cart
from .ledger import Ledger, Rejection
from .paypal import PaymentUnavailable, money_matches
from .agent_view import agent_view
from .plans import FinancialPlans


@dataclass(frozen=True)
class Principal:
    household: str
    identity: str
    role: str


class Gateway:
    def __init__(self, ledger: Ledger, catalog: Catalog, paypal=None, *,
                 period_id="prototype-period", proposal_limit=3, require_plan=False, drafter=None):
        if not isinstance(period_id, str) or not period_id or type(proposal_limit) is not int or proposal_limit < 1:
            raise ValueError("A trusted period ID and positive proposal limit are required.")
        self.ledger = ledger
        self.catalog = catalog
        self.paypal = paypal
        self.period_id = period_id
        self.proposal_limit = proposal_limit
        self.require_plan = require_plan
        self.drafter = drafter
        self.plans = FinancialPlans(ledger)

    @staticmethod
    def _owner(principal):
        if principal.role != "owner":
            raise Rejection("forbidden", "Financial plans and cash records are owner-only.")

    def plan(self, principal, action="get", body=None):
        self._owner(principal)
        if action == "get":
            return self.plans.get(principal.household)
        if action == "audit":
            return self.plans.audit(principal.household)
        from .finance import fields
        if action == "draft":
            fields(body, {"request", "timezone", "currency", "allow_model_processing"})
            if self.drafter is None:
                raise Rejection("draft_unavailable", "Model drafting is unavailable; manual plan preview and confirmation still work.")
            if self.plans.get(principal.household)["plan"] is not None:
                raise Rejection("draft_initial_only", "Use the owner revision/rollover controls for an existing plan.")
            result = self.drafter.draft(body["request"], body["timezone"], body["currency"],
                                        body["allow_model_processing"], clock=self.ledger.now)
            if result["status"] == "draft_ready":
                preview = self.plans.preview(principal.household, result["plan"], "activate")
                result.update(preview=preview, plan=preview["spec"], calculation=preview["summary"])
            return result
        if action == "preview":
            fields(body, {"plan", "mode"})
            return self.plans.preview(principal.household, body["plan"], body["mode"])
        if action == "confirm":
            fields(body, {"plan", "mode", "preview_hash"})
            return self.plans.confirm(principal.household, body["plan"], body["mode"], body["preview_hash"])
        if action == "cash-events":
            return self.plans.cash_event(principal.household, body)
        raise Rejection("not_found", "Unknown plan action.")

    def budget(self, principal):
        summary = self.ledger.summary(principal.household)
        if principal.role == "owner":
            return summary
        # Optional legacy endpoint: a conservative $50 floor, never exact headroom.
        available = summary["available_cents"] if summary.get("can_propose", True) else 0
        if self.require_plan and "plan_id" not in summary:
            available = 0
        return {"currency": "USD", "headroom_floor_cents": max(0, available) // 5000 * 5000}

    def owner_overview(self, principal):
        self._owner(principal)
        activity = self.ledger.owner_activity(principal.household)
        plan = self.plans.get(principal.household)
        events = activity["events"] + [
            {**event, "id": f"plan-{event['sequence']}", "purchase_id": None}
            for event in self.plans.audit(principal.household)["events"]]
        return {**plan, **activity, "events": sorted(events, key=lambda event: event["at"], reverse=True)}

    def audit(self, principal, purchase):
        self._purchase(principal, purchase, owner=True)
        return {"events": self.ledger.audit(purchase)}

    def _purchase(self, principal, purchase, *, owner=False):
        if owner and principal.role != "owner":
            raise Rejection("forbidden", "Agent tokens cannot grant consent or execute payments.")
        row = self.ledger.get(purchase)
        if row["household"] != principal.household or (
                principal.role != "owner" and row["agent"] != principal.identity):
            raise Rejection("forbidden", "Purchase is outside this token's scope.")
        return row

    def propose(self, principal: Principal, body: dict):
        if principal.role != "agent":
            raise Rejection("forbidden", "Use an agent token to propose a purchase.")
        if set(body) != {"items", "request_key"} or not isinstance(body["request_key"], str):
            raise Rejection("invalid_proposal", "Provide only items and request_key.")
        if self.require_plan and self.plans.get(principal.household)["plan"] is None:
            raise Rejection("plan_required", "The owner must confirm a financial plan first.")
        cart = self.catalog.quote(body["items"])
        counted_plan = self.ledger.claim_proposal(principal.household, principal.identity, self.period_id,
                                                 body["request_key"], cart.cart_hash, self.proposal_limit)
        try:
            purchase = self.ledger.reserve(principal.household, principal.identity, cart, body["request_key"],
                                           expected_plan_id=counted_plan)
            return agent_view({"decision": purchase["state"], "purchase": purchase})
        except Rejection as error:
            if error.code != "budget_exceeded":
                raise
            # Ledger.reserve constructs this internal detail from integer-cent accounting.
            offers = self.catalog.alternatives(cart, cast(int, error.details["available_cents"]))
            # One inexpensive feasible alternative, without disclosing the boundary.
            offers = sorted(offers, key=lambda o: o["total_cents"])[:1]
            return agent_view({"reason": error.code, "counteroffers": offers})

    def inspect(self, principal, purchase):
        row = self._purchase(principal, purchase)
        return row if principal.role == "owner" else agent_view(row)

    def approve(self, principal, purchase, expected_cart_hash):
        row = self._purchase(principal, purchase, owner=True)
        if expected_cart_hash != row["cart_hash"]:
            raise Rejection("cart_changed", "Consent must cover the displayed cart hash.")
        quoted = self.catalog.quote([{"sku": i["sku"], "quantity": i["quantity"]}
                                     for i in row["cart"]["items"]])
        return self.ledger.approve(purchase, quoted)

    def release(self, principal, purchase):
        self._purchase(principal, purchase, owner=True)
        return self.ledger.release(purchase)

    def checkout(self, principal, purchase):
        row = self._purchase(principal, purchase, owner=True)
        if row["state"] != "approved":
            raise Rejection("invalid_state", "Owner approval is required before creating checkout.")
        if not self.paypal:
            raise PaymentUnavailable("PayPal sandbox adapter is not configured.")
        cart = stored_cart(row)
        current = self.catalog.quote([{"sku": i.sku, "quantity": i.quantity} for i in cart.items])
        if current.cart_hash != cart.cart_hash:
            raise Rejection("cart_changed", "Catalog price changed; obtain a new approval.")
        result = self.paypal.create_order(row, cart)
        self.ledger.bind_order(purchase, result["order_id"])
        return result

    def execute(self, principal, purchase, action, permit):
        row = self._purchase(principal, purchase, owner=True)
        if not self.paypal:
            raise PaymentUnavailable("PayPal sandbox adapter is not configured.")
        if not row["order_id"]:
            raise Rejection("missing_order", "Create and approve PayPal checkout first.")
        cart = stored_cart(row)
        # Quote is rechecked before authorization, but authorized orders retain
        # their contracted prices even when later catalog prices change.
        if action == "authorize":
            cart = self.catalog.quote([{"sku": i.sku, "quantity": i.quantity} for i in cart.items])
            if row["state"] == "approved":
                # An early owner click must not strand a purchase in reconciliation.
                # No authorization request has been sent at this point.
                order = self.paypal.get_order(row["order_id"])
                self.paypal.validate_order(order, row, stored_cart(row))
                if order.get("status") != "APPROVED":
                    raise Rejection("buyer_approval_required", "Complete buyer approval on PayPal first.")
        operation = self.ledger.begin_payment(purchase, action, permit, cart)
        if not operation["execute"]:
            return operation["result"]
        op_id = operation["operation_id"]
        try:
            order = self.paypal.get_order(row["order_id"])
            self.paypal.validate_order(order, row, stored_cart(row))
            if action == "authorize":
                if order.get("status") != "APPROVED":
                    raise Rejection("buyer_approval_required", "Complete buyer approval on PayPal first.")
                result = self.paypal.authorize(row["order_id"], op_id)
                authorization = result["purchase_units"][0]["payments"]["authorizations"][0]
                if authorization["status"] != "CREATED" or not money_matches(
                        authorization["amount"], row["amount_cents"]):
                    raise PaymentUnavailable("Authorization result needs reconciliation.")
                return self.ledger.finish_payment(op_id, outcome="success", order_id=result["id"],
                                                  authorization_id=authorization["id"])
            if action == "capture":
                result = self.paypal.capture(row["authorization_id"], row["amount_cents"], op_id)
                if result["status"] != "COMPLETED" or not money_matches(result["amount"], row["amount_cents"]):
                    raise PaymentUnavailable("Capture result needs reconciliation.")
                return self.ledger.finish_payment(op_id, outcome="success", capture_id=result["id"])
            if action == "void":
                self.paypal.void(row["authorization_id"], op_id)
                authorization = self.paypal.get_authorization(row["authorization_id"])
                if authorization["status"] != "VOIDED":
                    raise PaymentUnavailable("Void result needs reconciliation.")
                return self.ledger.finish_payment(op_id, outcome="success")
        except (PaymentUnavailable, Rejection, KeyError, IndexError, TypeError):
            self.ledger.finish_payment(op_id, outcome="unknown")
            raise

    def refresh(self, principal, purchase, operation_id):
        row = self._purchase(principal, purchase, owner=True)
        operation = self.ledger.operation(operation_id)
        if operation["purchase"] != purchase:
            raise Rejection("forbidden", "Operation belongs to another purchase.")
        if not self.paypal:
            raise PaymentUnavailable("PayPal sandbox adapter is not configured.")
        order = self.paypal.get_order(row["order_id"])
        self.paypal.validate_order(order, row, stored_cart(row))
        payments = order["purchase_units"][0].get("payments", {})
        action = operation["action"]
        if action == "authorize":
            for authorization in payments.get("authorizations", []):
                if authorization["status"] == "CREATED" and money_matches(authorization["amount"], row["amount_cents"]):
                    return self.ledger.finish_payment(operation_id, outcome="success", order_id=row["order_id"],
                                                      authorization_id=authorization["id"])
        elif action == "capture":
            captures = payments.get("captures", [])
            if len(captures) == 1 and captures[0]["status"] == "COMPLETED" and money_matches(
                    captures[0]["amount"], row["amount_cents"]):
                return self.ledger.finish_payment(operation_id, outcome="success", capture_id=captures[0]["id"])
        elif action == "void":
            authorization = self.paypal.get_authorization(row["authorization_id"])
            if authorization["status"] == "VOIDED":
                return self.ledger.finish_payment(operation_id, outcome="success")
        return {"decision": "pending", "purchase": row,
                "message": "Payment outcome unresolved. Budget remains committed."}
