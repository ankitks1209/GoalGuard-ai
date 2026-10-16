"""Reviewed financial semantics with fixed dates and isolated SQLite files."""

from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from goalguard import Cart, Item, Ledger, Rejection
from goalguard.catalog import Catalog
from goalguard.gateway import Gateway, Principal
from goalguard.plans import FinancialPlans
from server import make_handler


class Clock:
    value = datetime(2026, 10, 15, 12, tzinfo=timezone.utc).timestamp()

    def __call__(self):
        return self.value


def example():
    return {"title": "Household plan", "timezone": "UTC", "currency": "USD",
            "opening_cash_cents": 60000, "buffer_cents": 5000,
            "next_income": {"id": "pay-oct", "due_date": "2026-10-20", "amount_cents": 40000},
            "bills": [{"id": "bill-1", "name": "Utilities", "amount_cents": 10000, "due_date": "2026-10-25"}],
            "goal": {"id": "goal-1", "title": "Recording equipment", "target_cents": 60000,
                     "current_saved_cents": 30000, "target_date": "2026-12-31", "contribution_cents": 10000}}


class FinancialPlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "ledger.sqlite"
        self.clock = Clock()
        self.ledger = Ledger(self.path, now=self.clock)
        self.ledger.create_household("demo-home", 0, 0)
        self.plans = FinancialPlans(self.ledger)
        self.spec = example()
        self.cart = Cart("demo-merchant", (Item("unit", 1, 22000),))

    def tearDown(self):
        self.tmp.cleanup()

    def confirm(self, spec=None, mode="activate"):
        spec = spec or self.spec
        preview = self.plans.preview("demo-home", spec, mode)
        return self.plans.confirm("demo-home", spec, mode, preview["preview_hash"])

    def cash(self, kind, amount, ref=None, key="event-1"):
        return self.plans.cash_event("demo-home", {"event_id": key, "kind": kind,
                                                 "amount_cents": amount, "reference_id": ref})

    def expect(self, code, fn, *args, **kwargs):
        with self.assertRaises(Rejection) as caught:
            fn(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)

    def reserve(self, key="purchase-1", cart=None):
        return self.ledger.reserve("demo-home", "agent-a", cart or self.cart, key)

    def authorize(self):
        purchase = self.reserve()
        approved = self.ledger.approve(purchase["id"], self.cart)
        op = self.ledger.begin_payment(purchase["id"], "authorize", approved["permit"], self.cart)
        self.ledger.finish_payment(op["operation_id"], outcome="success", order_id="order-1", authorization_id="auth-1")
        return approved

    def capture(self, purchase):
        op = self.ledger.begin_payment(purchase["id"], "capture", purchase["permit"], self.cart)
        self.ledger.finish_payment(op["operation_id"], outcome="success", capture_id="capture-1")

    def test_preview_is_saved_without_purchase_authority(self):
        self.plans.preview("demo-home", self.spec)
        view = self.plans.get("demo-home")
        self.assertIsNone(view["plan"])
        self.assertEqual(view["draft"]["spec"], self.spec)
        gateway = Gateway(self.ledger, Catalog(), require_plan=True)
        self.expect("plan_required", gateway.propose, Principal("demo-home", "a", "agent"),
                    {"items": [{"sku": "mic-standard", "quantity": 1}], "request_key": "draft"})

    def test_cash_and_forecast_are_distinct_and_named(self):
        view = self.confirm()
        self.assertEqual(view["available_cents"], 35000)
        self.assertEqual(view["projected_surplus_cents"], 75000)
        self.assertEqual(view["bills"][0]["name"], "Utilities")
        self.assertEqual(view["goal"]["suggested_contribution_cents"], 10000)
        self.reserve()
        self.assertEqual(self.ledger.summary("demo-home")["available_cents"], 13000)

    def test_month_end_cliff_protects_rent_until_income(self):
        self.clock.value = datetime(2026, 10, 30, 12, tzinfo=timezone.utc).timestamp()
        self.spec.update(opening_cash_cents=50000, buffer_cents=0, goal=None,
                         next_income={"id": "nov-pay", "due_date": "2026-11-05", "amount_cents": 100000},
                         bills=[{"id": "rent", "name": "Rent", "amount_cents": 40000, "due_date": "2026-11-01"}])
        view = self.confirm()
        self.assertEqual(view["bill_cutoff_exclusive"], "2026-11-06")
        self.assertEqual(view["available_cents"], 10000)
        self.expect("budget_exceeded", self.reserve, cart=Cart("m", (Item("unit", 1, 15000),)))

    def test_bills_on_payday_and_overdue_count_once_future_excluded(self):
        self.spec["next_income"]["due_date"] = "2026-11-05"
        self.spec["bills"] = [{"id": key, "name": key, "amount_cents": 1000, "due_date": due}
                              for key, due in [("old", "2026-10-01"), ("payday", "2026-11-05"), ("later", "2026-11-06")]]
        view = self.confirm()
        self.assertEqual(view["protected_bills_cents"], 2000)
        self.assertEqual(len(view["bills"]), 3)

    def test_infeasible_and_waiting_drafts_cannot_activate(self):
        for opening, income, expected in [(0, 100, "infeasible"), (0, 40000, "waiting_for_income")]:
            with self.subTest(expected=expected):
                spec = deepcopy(self.spec)
                spec["opening_cash_cents"] = opening
                spec["next_income"]["amount_cents"] = income
                preview = self.plans.preview("demo-home", spec)
                self.assertEqual(preview["summary"]["status"], expected)
                self.assertLess(preview["summary"]["available_cents"], 0)
                self.expect("plan_not_ready", self.plans.confirm, "demo-home", spec, "activate", preview["preview_hash"])

    def test_zero_capacity_can_activate(self):
        self.spec["opening_cash_cents"] = 25000
        self.assertEqual(self.confirm()["status"], "zero_capacity")
        self.expect("budget_exceeded", self.reserve)

    def test_missing_income_date_requires_clarification(self):
        self.spec["next_income"] = None
        preview = self.plans.preview("demo-home", self.spec)
        self.assertEqual(preview["summary"]["status"], "needs_income_date")
        self.expect("plan_not_ready", self.plans.confirm, "demo-home", self.spec, "activate", preview["preview_hash"])

    def test_late_income_blocks_until_received(self):
        self.confirm()
        self.clock.value = datetime(2026, 10, 21, 12, tzinfo=timezone.utc).timestamp()
        self.assertEqual(self.ledger.summary("demo-home")["status"], "income_overdue")
        self.expect("plan_not_ready", self.reserve)
        self.cash("income", 40000, "pay-oct")
        self.assertEqual(self.ledger.summary("demo-home")["available_cents"], 75000)
        self.assertEqual(self.ledger.summary("demo-home")["expected_unreceived_income_cents"], 0)
        self.assertEqual(self.ledger.summary("demo-home")["status"], "needs_next_income")
        self.expect("plan_not_ready", self.reserve)
        self.spec["next_income"] = {"id": "nov-pay", "due_date": "2026-11-05", "amount_cents": 40000}
        self.confirm(mode="revise")
        self.reserve()

    def test_received_payday_cannot_leave_next_month_rent_unprotected(self):
        self.spec["next_income"]["due_date"] = "2026-10-16"
        self.spec["bills"] = [{"id": "rent", "name": "Rent", "amount_cents": 40000, "due_date": "2026-11-01"}]
        self.confirm()
        self.cash("income", 40000, "pay-oct")
        self.expect("plan_not_ready", self.reserve)
        self.spec["next_income"] = {"id": "nov-pay", "due_date": "2026-11-05", "amount_cents": 40000}
        after = self.confirm(mode="revise")
        self.assertEqual(after["protected_bills_cents"], 40000)
        self.assertEqual(after["available_cents"], 45000)

    def test_partial_income_does_not_clear_overdue(self):
        self.confirm()
        self.clock.value = datetime(2026, 10, 21, 12, tzinfo=timezone.utc).timestamp()
        self.cash("income", 10000, "pay-oct")
        self.assertEqual(self.ledger.summary("demo-home")["status"], "income_overdue")

    def test_partial_month_goal_uses_full_integer_ceil_installment(self):
        self.clock.value = datetime(2026, 10, 30, 12, tzinfo=timezone.utc).timestamp()
        self.spec["next_income"]["due_date"] = "2026-11-05"
        self.spec["goal"].update(target_cents=30001, current_saved_cents=0, contribution_cents=10001)
        view = self.confirm()["goal"]
        self.assertEqual(view["suggested_contribution_cents"], 10001)
        self.assertEqual(view["contribution_opportunities"], 3)
        self.assertTrue(view["partial_month_counts_in_full"])

    def test_lower_goal_override_explicitly_off_track(self):
        self.spec["goal"]["contribution_cents"] = 5000
        self.assertTrue(self.confirm()["goal"]["schedule_off_track"])

    def test_final_installment_is_capped_at_remaining_goal(self):
        self.spec["goal"].update(target_cents=30100, contribution_cents=10000)
        self.assertEqual(self.confirm()["remaining_goal_contribution_cents"], 100)

    def test_bill_payment_pairs_cash_and_protection_atomically(self):
        self.confirm()
        after = self.cash("bill_payment", 10000, "bill-1")["summary"]
        self.assertEqual(after["cash_base_cents"], 50000)
        self.assertEqual(after["protected_bills_cents"], 0)
        self.assertEqual(after["available_cents"], 35000)
        self.expect("invalid_cash_event", self.cash, "bill_payment", 1, "bill-1", "extra")
        self.assertEqual(self.ledger.summary("demo-home")["cash_base_cents"], 50000)

    def test_savings_deposit_pairs_cash_contribution_and_saved_balance(self):
        self.confirm()
        after = self.cash("savings_deposit", 4000, "goal-1")["summary"]
        self.assertEqual(after["cash_base_cents"], 56000)
        self.assertEqual(after["remaining_goal_contribution_cents"], 6000)
        self.assertEqual(after["goal"]["current_saved_cents"], 34000)
        self.assertEqual(after["goal"]["suggested_contribution_cents"], 10000)
        self.assertEqual(after["available_cents"], 35000)

    def test_deposit_above_installment_reduces_extra_cash(self):
        self.confirm()
        after = self.cash("savings_deposit", 15000, "goal-1")["summary"]
        self.assertEqual(after["remaining_goal_contribution_cents"], 0)
        self.assertEqual(after["goal"]["current_saved_cents"], 45000)
        self.assertEqual(after["available_cents"], 30000)

    def test_deposit_beyond_goal_does_not_recompute_original_schedule(self):
        self.confirm()
        after = self.cash("savings_deposit", 40000, "goal-1")["summary"]
        self.assertEqual(after["goal"]["suggested_contribution_cents"], 10000)
        self.assertEqual(after["goal"]["remaining_goal_cents"], 0)
        self.assertEqual(after["remaining_goal_contribution_cents"], 0)

    def test_title_revision_preserves_fulfilled_installment(self):
        self.confirm()
        self.cash("savings_deposit", 4000, "goal-1")
        spec = self.plans.get("demo-home")["plan"]["spec"]
        spec["title"] = "New label"
        after = self.confirm(spec, "revise")
        self.assertEqual(after["remaining_goal_contribution_cents"], 6000)
        self.assertEqual(after["goal"]["suggested_contribution_cents"], 10000)

    def test_cash_event_retry_and_conflict(self):
        self.confirm()
        self.cash("external_inflow", 100)
        retry = self.cash("external_inflow", 100)
        self.assertFalse(retry["recorded"])
        self.expect("idempotency_conflict", self.cash, "external_inflow", 200)
        self.assertEqual(self.ledger.summary("demo-home")["cash_base_cents"], 60100)

    def test_cash_correction_records_negative_truth_and_preserves_authorization(self):
        self.confirm()
        purchase = self.authorize()
        after = self.cash("external_outflow", 40000)["summary"]
        self.assertEqual(after["available_cents"], -27000)
        self.assertEqual(after["encumbered_cents"], 22000)
        self.expect("plan_not_ready", self.reserve, "new")
        self.capture(purchase)
        self.assertEqual(self.ledger.summary("demo-home")["available_cents"], -27000)

    def test_cash_receipt_releases_pending_approval(self):
        self.confirm()
        row = self.reserve()
        approved = self.ledger.approve(row["id"], self.cart)
        self.cash("external_inflow", 100)
        self.assertEqual(self.ledger.get(row["id"])["state"], "released")
        self.expect("invalid_approval", self.ledger.begin_payment, row["id"], "authorize", approved["permit"], self.cart)

    def test_financial_revision_releases_approvals_and_advances_policy(self):
        old = self.confirm()
        row = self.reserve()
        approved = self.ledger.approve(row["id"], self.cart)
        self.spec["buffer_cents"] += 1000
        preview = self.plans.preview("demo-home", self.spec, "revise")
        self.assertEqual(preview["releases_purchase_ids"], [row["id"]])
        new = self.confirm(mode="revise")
        self.assertEqual(new["policy_version"], old["policy_version"] + 1)
        self.assertEqual(new["available_cents"], 34000)
        self.expect("invalid_approval", self.ledger.begin_payment, row["id"], "authorize", approved["permit"], self.cart)

    def test_title_and_forecast_only_edits_preserve_approval(self):
        old = self.confirm()
        row = self.reserve()
        approved = self.ledger.approve(row["id"], self.cart)
        self.spec["title"] = "Renamed"
        self.spec["goal"]["title"] = "Renamed goal"
        self.spec["next_income"]["amount_cents"] += 100
        new = self.confirm(mode="revise")
        self.assertEqual(new["policy_version"], old["policy_version"])
        self.assertTrue(self.ledger.begin_payment(row["id"], "authorize", approved["permit"], self.cart)["execute"])

    def test_authorized_purchase_can_capture_after_revision(self):
        self.confirm()
        purchase = self.authorize()
        self.spec["buffer_cents"] += 1000
        self.confirm(mode="revise")
        self.capture(purchase)
        self.assertEqual(self.ledger.summary("demo-home")["spent_cents"], 22000)
        self.assertEqual(self.ledger.summary("demo-home")["available_cents"], 12000)

    def test_revision_waits_only_for_inflight_or_unknown_payments(self):
        self.confirm()
        purchase = self.reserve()
        approved = self.ledger.approve(purchase["id"], self.cart)
        op = self.ledger.begin_payment(purchase["id"], "authorize", approved["permit"], self.cart)
        self.spec["buffer_cents"] += 1000
        for unknown in [False, True]:
            if unknown:
                self.ledger.finish_payment(op["operation_id"], outcome="unknown")
            preview = self.plans.preview("demo-home", self.spec, "revise")
            self.assertEqual(preview["activation_blocked_by"], "payment_unresolved")
            self.expect("plan_not_ready", self.plans.confirm, "demo-home", self.spec, "revise", preview["preview_hash"])
        self.cash("external_outflow", 1000)
        self.assertEqual(self.ledger.summary("demo-home")["encumbered_cents"], 22000)

    def test_stale_preview_rejected_if_reservations_change(self):
        self.confirm()
        self.spec["buffer_cents"] += 1000
        preview = self.plans.preview("demo-home", self.spec, "revise")
        self.reserve()
        self.expect("stale_plan_preview", self.plans.confirm, "demo-home", self.spec, "revise", preview["preview_hash"])

    def test_revision_cannot_spend_against_forecast_or_erase_authorized_obligation(self):
        self.confirm()
        self.authorize()
        self.spec["buffer_cents"] = 50000
        preview = self.plans.preview("demo-home", self.spec, "revise")
        self.assertEqual(preview["summary"]["status"], "waiting_for_income")
        self.expect("plan_not_ready", self.plans.confirm, "demo-home", self.spec, "revise", preview["preview_hash"])
        self.assertEqual(self.ledger.summary("demo-home")["encumbered_cents"], 22000)

    def test_opening_cash_and_timezone_cannot_be_rewritten(self):
        self.confirm()
        changed = deepcopy(self.spec)
        changed["opening_cash_cents"] += 100
        self.expect("cash_event_required", self.plans.preview, "demo-home", changed, "revise")
        changed = deepcopy(self.spec)
        changed["timezone"] = "Asia/Kolkata"
        self.expect("immutable_period", self.plans.preview, "demo-home", changed, "revise")

    def test_revision_and_authorization_race_serializes(self):
        self.confirm()
        purchase = self.reserve()
        approved = self.ledger.approve(purchase["id"], self.cart)
        self.spec["buffer_cents"] += 1000
        preview = self.plans.preview("demo-home", self.spec, "revise")
        barrier = threading.Barrier(2)
        def action(which):
            barrier.wait()
            try:
                if which == "revise":
                    return self.plans.confirm("demo-home", self.spec, "revise", preview["preview_hash"])
                return self.ledger.begin_payment(purchase["id"], "authorize", approved["permit"], self.cart)
            except Rejection as error:
                return error.code
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(action, ["revise", "authorize"]))
        self.assertEqual(sum(isinstance(r, dict) for r in results), 1)
        self.assertIn(next(r for r in results if isinstance(r, str)), ["stale_plan_preview", "invalid_approval"])

    def test_concurrent_reservations_use_same_plan_and_database(self):
        self.confirm()
        barrier = threading.Barrier(2)
        def action(key):
            ledger = Ledger(self.path, now=self.clock)
            barrier.wait()
            try:
                return ledger.reserve("demo-home", key, self.cart, key)["state"]
            except Rejection as error:
                return error.code
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(action, ["a", "b"]))
        self.assertCountEqual(results, ["reserved", "budget_exceeded"])

    def test_period_end_blocks_new_purchases(self):
        view = self.confirm()
        self.clock.value = view["period_end"]
        self.assertEqual(self.ledger.summary("demo-home")["status"], "rollover_required")
        self.expect("plan_not_ready", self.reserve)

    def test_reporting_period_uses_household_timezone(self):
        self.spec["timezone"] = "Asia/Kolkata"
        view = self.confirm()
        expected = datetime(2026, 10, 31, 18, 30, tzinfo=timezone.utc).timestamp()
        self.assertEqual(view["period_end"], expected)
        self.clock.value = expected
        self.expect("plan_not_ready", self.reserve)

    def test_rollover_preserves_partial_bill_payment_without_double_deduction(self):
        old = self.confirm()
        self.cash("bill_payment", 4000, "bill-1")
        self.clock.value = old["period_end"]
        self.spec["opening_cash_cents"] = 56000
        self.spec["bills"][0]["amount_cents"] = 6000
        self.spec["next_income"] = {"id": "nov-pay", "due_date": "2026-11-05", "amount_cents": 40000}
        after = self.confirm(mode="rollover")
        self.assertEqual(after["protected_bills_cents"], 6000)
        self.assertEqual(after["available_cents"], 35000)

    def test_rollover_carries_cash_and_authorization_once(self):
        old = self.confirm()
        purchase = self.authorize()
        self.clock.value = old["period_end"]
        self.spec["next_income"] = {"id": "nov-pay", "due_date": "2026-11-05", "amount_cents": 40000}
        new = self.confirm(mode="rollover")
        self.assertNotEqual(new["plan_id"], old["plan_id"])
        self.assertEqual(new["encumbered_cents"], 22000)
        carry = next(e for e in self.ledger.audit(purchase["id"]) if e["event"] == "carried_to_plan")
        self.assertEqual(carry["details"], {"from_plan": old["plan_id"], "to_plan": new["plan_id"]})
        self.capture(purchase)
        summary = self.ledger.summary("demo-home")
        self.assertEqual(summary["spent_cents"], 22000)
        self.assertEqual(summary["encumbered_cents"], 0)
        self.assertEqual(summary["available_cents"], 13000)

    def test_rollover_rebases_old_captured_spend_and_keeps_unpaid_bills(self):
        old = self.confirm()
        purchase = self.authorize()
        self.capture(purchase)
        self.clock.value = old["period_end"]
        self.spec["opening_cash_cents"] = 38000
        self.spec["next_income"] = {"id": "nov-pay", "due_date": "2026-11-05", "amount_cents": 40000}
        missing = deepcopy(self.spec)
        missing["bills"] = []
        self.expect("missing_carried_bill", self.plans.preview, "demo-home", missing, "rollover")
        new = self.confirm(mode="rollover")
        self.assertEqual(new["spent_cents"], 0)
        self.assertEqual(new["cash_base_cents"], 38000)
        self.assertEqual(new["available_cents"], 13000)

    def test_proposal_quota_uses_plan_period_and_survives_revision(self):
        view = self.confirm()
        for i in range(3):
            self.ledger.claim_proposal("demo-home", "agent-a", "ignored", str(i), "hash", 3)
        self.spec["buffer_cents"] += 100
        view = self.confirm(mode="revise")
        self.expect("proposal_limit", self.ledger.claim_proposal, "demo-home", "agent-a", "different", "fourth", "hash", 3)
        self.clock.value = view["period_end"]
        self.spec["next_income"] = {"id": "nov-pay", "due_date": "2026-11-05", "amount_cents": 40000}
        self.confirm(mode="rollover")
        self.ledger.claim_proposal("demo-home", "agent-a", "ignored", "fourth", "hash", 3)

    def test_legacy_captured_spend_is_not_silently_migrated(self):
        self.ledger.create_household("legacy", 60000, 0)
        purchase = self.ledger.reserve("legacy", "agent", self.cart, "one")
        approved = self.ledger.approve(purchase["id"], self.cart)
        op = self.ledger.begin_payment(purchase["id"], "authorize", approved["permit"], self.cart)
        self.ledger.finish_payment(op["operation_id"], outcome="success", order_id="legacy-order", authorization_id="legacy-auth")
        op = self.ledger.begin_payment(purchase["id"], "capture", approved["permit"], self.cart)
        self.ledger.finish_payment(op["operation_id"], outcome="success", capture_id="legacy-capture")
        self.expect("legacy_migration_required", self.plans.preview, "legacy", self.spec)
        self.assertEqual(self.ledger.summary("legacy")["spent_cents"], 22000)

    def test_quota_claim_cannot_fund_purchase_in_a_different_period(self):
        view = self.confirm()
        counted = self.ledger.claim_proposal("demo-home", "agent-a", "ignored", "racing", self.cart.cart_hash, 3)
        self.clock.value = view["period_end"]
        self.spec["next_income"] = {"id": "nov-pay", "due_date": "2026-11-05", "amount_cents": 40000}
        self.confirm(mode="rollover")
        self.expect("plan_not_ready", self.ledger.reserve, "demo-home", "agent-a", self.cart, "racing", expected_plan_id=counted)

    def test_refund_is_deduplicated_cash_credit_not_capture_reversal(self):
        self.confirm()
        purchase = self.authorize()
        self.capture(purchase)
        after = self.cash("refund", 1000, purchase["id"])["summary"]
        self.assertEqual(after["spent_cents"], 22000)
        self.assertEqual(after["available_cents"], 14000)
        self.assertFalse(self.cash("refund", 1000, purchase["id"])["recorded"])
        self.expect("invalid_cash_event", self.cash, "refund", 22000, purchase["id"], "excess")

    def test_plan_is_private_to_owner_including_denials(self):
        self.confirm()
        gateway = Gateway(self.ledger, Catalog(), require_plan=True)
        agent = Principal("demo-home", "agent-a", "agent")
        for action in ["get", "preview", "confirm", "cash-events", "audit"]:
            self.expect("forbidden", gateway.plan, agent, action, {})
        denied = gateway.propose(agent, {"items": [{"sku": "vacuum-standard", "quantity": 2}], "request_key": "denied"})
        public = json.dumps(denied)
        for private in ["Utilities", "Recording equipment", "buffer_cents", "current_saved_cents", "projected_surplus_cents"]:
            self.assertNotIn(private, public)

    def test_restart_preserves_plan_paid_bill_and_signing_key(self):
        self.confirm()
        self.cash("bill_payment", 10000, "bill-1")
        key = self.ledger.key
        restarted = Ledger(self.path, now=self.clock)
        self.assertEqual(restarted.key, key)
        self.assertEqual(restarted.summary("demo-home")["protected_bills_cents"], 0)

    def test_reject_fractional_money_currency_duplicate_ids_and_past_goal(self):
        for field, value in [("opening_cash_cents", 0.5), ("buffer_cents", True), ("currency", "INR")]:
            with self.subTest(field=field):
                spec = deepcopy(self.spec)
                spec[field] = value
                with self.assertRaises(Rejection):
                    self.plans.preview("demo-home", spec)
        duplicate = deepcopy(self.spec)
        duplicate["bills"] *= 2
        self.expect("invalid_plan", self.plans.preview, "demo-home", duplicate)
        self.spec["goal"]["target_date"] = "2026-10-01"
        self.expect("invalid_plan", self.plans.preview, "demo-home", self.spec)


class PlanHTTPTests(unittest.TestCase):
    def test_owner_plan_routes_and_agent_denial_over_tcp(self):
        with tempfile.TemporaryDirectory() as folder:
            ledger = Ledger(Path(folder) / "ledger.sqlite", now=Clock())
            ledger.create_household("demo-home", 0, 0)
            handler = make_handler(Gateway(ledger, Catalog(), require_plan=True), {"owner": "o" * 32, "agent-a": "a" * 32})
            server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            def request(path, body=None, role="owner"):
                token = ("o" if role == "owner" else "a") * 32
                req = Request(f"http://127.0.0.1:{server.server_port}/v1/plan" + path,
                              data=json.dumps(body).encode() if body is not None else None,
                              headers={"Authorization": "Bearer " + token, "Content-Type": "application/json"})
                with urlopen(req, timeout=5) as response:
                    return json.load(response)
            try:
                preview = request("/preview", {"plan": example(), "mode": "activate"})
                active = request("/confirm", {"plan": example(), "mode": "activate", "preview_hash": preview["preview_hash"]})
                self.assertEqual(active["available_cents"], 35000)
                with self.assertRaises(HTTPError) as caught:
                    request("", role="agent")
                self.assertEqual(caught.exception.code, 403)
                self.assertEqual(json.load(caught.exception), {"decision": "denied", "reason": "forbidden"})
                caught.exception.close()
                self.assertEqual(request("")["plan"]["plan_id"], active["plan_id"])
            finally:
                server.shutdown()
                server.server_close()
                thread.join()
