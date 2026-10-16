from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from goalguard import Ledger, Rejection
from goalguard.agent_view import agent_view
from goalguard.catalog import Catalog, PRODUCTS
from goalguard.gateway import Gateway, Principal
from goalguard.runner import ProposalRunner
from probe_evaluate import probe


class AgentControlsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "ledger.sqlite"
        self.ledger = Ledger(self.path)
        self.ledger.create_household("home", 35_000, 0)
        self.catalog = Catalog(products=deepcopy(PRODUCTS))
        self.gateway = Gateway(self.ledger, self.catalog)
        self.agent = Principal("home", "a", "agent")
        self.owner = Principal("home", "owner", "owner")

    def body(self, key, quantity=10):
        return {"items": [{"sku": "mic-standard", "quantity": quantity}], "request_key": key}

    def test_runner_rejects_second_revision_without_calling_gateway(self):
        runner = ProposalRunner(self.gateway, self.agent)
        with patch.object(self.gateway, "propose", wraps=self.gateway.propose) as propose:
            self.assertEqual(runner.call("propose_purchase", {"items": self.body("a", 10)["items"]})["decision"], "denied")
            self.assertEqual(runner.call("propose_purchase", {"items": self.body("b", 9)["items"]})["decision"], "denied")
            with self.assertRaises(Rejection) as caught:
                runner.call("propose_purchase", {"items": self.body("c", 8)["items"]})
            self.assertEqual(caught.exception.code, "revision_limit")
            self.assertEqual(propose.call_count, 2)

    def test_one_revision_can_reserve_then_stops(self):
        runner = ProposalRunner(self.gateway, self.agent)
        runner.call("propose_purchase", {"items": self.body("a")["items"]})
        self.assertEqual(runner.call("propose_purchase", {"items": self.body("b", 1)["items"]})["decision"], "reserved")
        with self.assertRaises(Rejection) as caught:
            runner.call("get_catalog", {})
        self.assertEqual(caught.exception.code, "run_complete")

    def test_unchanged_denial_does_not_call_gateway_again(self):
        runner = ProposalRunner(self.gateway, self.agent)
        args = {"items": self.body("a")["items"]}
        with patch.object(self.gateway, "propose", wraps=self.gateway.propose) as propose:
            runner.call("propose_purchase", args)
            runner.call("propose_purchase", args)
            self.assertEqual(propose.call_count, 1)

    def test_runner_counts_catalog_reads_against_tool_limit(self):
        runner = ProposalRunner(self.gateway, self.agent)
        for _ in range(8):
            runner.call("get_catalog", {})
        with self.assertRaises(Rejection) as caught:
            runner.call("get_catalog", {})
        self.assertEqual(caught.exception.code, "tool_limit")

    def test_runner_unexpected_error_does_not_expose_private_text(self):
        runner = ProposalRunner(self.gateway, self.agent)
        with patch.object(self.gateway, "propose", side_effect=RuntimeError("PRIVATE-RENT-AND-SAVINGS")):
            result = runner.call("propose_purchase", {"items": self.body("a", 1)["items"]})
        self.assertEqual(result, {"decision": "denied", "reason": "internal_error"})

    def test_runner_does_not_expose_budget_or_owner_tools(self):
        runner = ProposalRunner(self.gateway, self.agent)
        for tool in ("get_budget", "approve", "capture", "audit"):
            self.assertEqual(runner.call(tool, {}), {"decision": "denied", "reason": "invalid_proposal"})

    def test_transport_retry_retains_request_key_and_one_reservation(self):
        runner = ProposalRunner(self.gateway, self.agent)
        original = self.gateway.propose
        calls = []
        def lose_first(actor, body):
            calls.append(body["request_key"])
            result = original(actor, body)
            if len(calls) == 1:
                raise TimeoutError("Synthetic response loss")
            return result
        with patch.object(self.gateway, "propose", side_effect=lose_first):
            args = {"items": self.body("a", 1)["items"]}
            self.assertEqual(runner.call("propose_purchase", args)["reason"], "outcome_unknown")
            self.assertEqual(runner.call("propose_purchase", args)["decision"], "reserved")
        self.assertEqual(calls[0], calls[1])
        self.assertEqual(runner.proposals, 1)
        self.assertEqual(self.ledger.summary("home")["encumbered_cents"], 22_000)

    def test_uncertain_result_cannot_switch_to_another_cart(self):
        runner = ProposalRunner(self.gateway, self.agent)
        with patch.object(self.gateway, "propose", side_effect=TimeoutError):
            runner.call("propose_purchase", {"items": self.body("a")["items"]})
            with self.assertRaises(Rejection) as caught:
                runner.call("propose_purchase", {"items": self.body("b", 9)["items"]})
        self.assertEqual(caught.exception.code, "outcome_unknown")

    def test_gateway_quota_survives_gateway_and_ledger_restart(self):
        for i in range(3):
            self.gateway.propose(self.agent, self.body(str(i)))
        restarted = Gateway(Ledger(self.path), self.catalog)
        with self.assertRaises(Rejection) as caught:
            restarted.propose(self.agent, self.body("fourth"))
        self.assertEqual(caught.exception.code, "proposal_limit")

    def test_quota_is_atomic_across_concurrent_denied_proposals(self):
        def propose(i):
            try:
                return self.gateway.propose(self.agent, self.body(str(i))).get("reason")
            except Rejection as error:
                return error.code
        with ThreadPoolExecutor(max_workers=10) as pool:
            results = list(pool.map(propose, range(10)))
        self.assertEqual(results.count("budget_exceeded"), 3)
        self.assertEqual(results.count("proposal_limit"), 7)

    def test_same_key_retry_does_not_spend_another_quota_slot(self):
        for _ in range(5):
            self.gateway.propose(self.agent, self.body("one"))
        self.gateway.propose(self.agent, self.body("two"))
        self.gateway.propose(self.agent, self.body("three"))
        with self.assertRaises(Rejection):
            self.gateway.propose(self.agent, self.body("four"))

    def test_changed_cart_cannot_reuse_a_denied_key_to_probe(self):
        self.gateway.propose(self.agent, self.body("one", 10))
        with self.assertRaises(Rejection) as caught:
            self.gateway.propose(self.agent, self.body("one", 9))
        self.assertEqual(caught.exception.code, "idempotency_conflict")

    def test_quota_scope_is_trusted_agent_and_period(self):
        for i in range(3):
            self.gateway.propose(self.agent, self.body(str(i)))
        other = Principal("home", "b", "agent")
        self.assertEqual(self.gateway.propose(other, self.body("one"))["reason"], "budget_exceeded")
        new_period = Gateway(self.ledger, self.catalog, period_id="owner-confirmed-next-period")
        self.assertEqual(new_period.propose(self.agent, self.body("new"))["reason"], "budget_exceeded")
        with self.assertRaises(Rejection):
            self.gateway.propose(self.agent, {**self.body("injected"), "period_id": "bypass"})

    def test_budget_is_coarse_for_agent_and_full_for_owner(self):
        self.gateway.propose(self.agent, self.body("accepted", 1))
        self.assertEqual(self.gateway.budget(self.agent), {"currency": "USD", "headroom_floor_cents": 10_000})
        self.assertEqual(self.gateway.budget(self.owner)["available_cents"], 13_000)

    def test_denial_and_counteroffer_have_no_private_financial_details(self):
        secret = "PRIVATE-HOUSEHOLD-RENT-AND-GOAL"
        error = Rejection("budget_exceeded", secret, available_cents=13_000,
                          bill_names=[secret], buffer=secret, savings_goal=secret)
        with patch.object(self.ledger, "reserve", side_effect=error):
            result = self.gateway.propose(self.agent, {"items": [{"sku": "vacuum-standard", "quantity": 1}], "request_key": "one"})
        self.assertEqual(set(result), {"decision", "reason", "counteroffers"})
        self.assertEqual(len(result["counteroffers"]), 1)
        self.assertEqual(result["counteroffers"][0]["total_cents"], 10_000)
        self.assertNotIn(secret, json.dumps(result))
        self.assertNotIn("available_cents", json.dumps(result))

    def test_purchase_view_uses_allowlist_for_nested_private_fields(self):
        row = self.gateway.propose(self.agent, self.body("one", 1))["purchase"]
        original = self.ledger.get(row["id"])
        private = "PRIVATE-SAVINGS-TARGET"
        tainted = {**original, "bill_names": [private], "buffer": private,
                   "savings_goal": private, "cart": {"private_goal": private}}
        with patch.object(self.ledger, "get", return_value=tainted):
            self.assertNotIn(private, json.dumps(self.gateway.inspect(self.agent, row["id"])))
            self.assertEqual(self.gateway.inspect(self.owner, row["id"])["buffer"], private)

    def test_owners_audit_is_not_an_agent_tool(self):
        row = self.gateway.propose(self.agent, self.body("one", 1))["purchase"]
        with self.assertRaises(Rejection) as caught:
            self.gateway.audit(self.agent, row["id"])
        self.assertEqual(caught.exception.code, "forbidden")

    def test_allowlist_drops_unexpected_denial_and_catalog_fields(self):
        secret = "PRIVATE-BUFFER-AND-GOAL"
        self.assertNotIn(secret, json.dumps(agent_view({"reason": "invalid_cart", "message": secret, "details": {"bill": secret}})))
        self.assertNotIn(secret, json.dumps(agent_view({"products": [{"sku": "x", "buffer": secret, "savings_goal": secret}]})))

    def test_binary_search_is_limited_but_still_leaks_an_interval(self):
        capped = probe(73, 3)
        self.assertEqual(capped["evaluated_proposals"], 3)
        self.assertTrue(capped["blocked_by_quota"])
        self.assertEqual(capped["recovered_interval_cents"], [62, 74])
        self.assertFalse(capped["exact_recovery"])
        control = probe(73, 32)
        self.assertEqual(control["recovered_interval_cents"], [73, 73])
        self.assertTrue(control["exact_recovery"])
