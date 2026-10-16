"""Failure-first local demo. No LLM calls or PayPal payment requests."""

from concurrent.futures import ThreadPoolExecutor
import argparse
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile

from goalguard import Ledger
from goalguard.catalog import Catalog
from goalguard.gateway import Gateway, Principal


def sample_plan():
    today = datetime.now(timezone.utc).date()
    deadline_month = today.year * 12 + today.month - 1 + 2
    deadline = today.replace(year=deadline_month // 12, month=deadline_month % 12 + 1, day=28)
    return {"title": "Demo household", "timezone": "UTC", "currency": "USD",
            "opening_cash_cents": 60000, "buffer_cents": 5000,
            "next_income": {"id": "demo-next-pay", "due_date": (today + timedelta(days=5)).isoformat(), "amount_cents": 40000},
            "bills": [{"id": "demo-bill", "name": "Utilities", "amount_cents": 10000, "due_date": (today + timedelta(days=1)).isoformat()}],
            "goal": {"id": "demo-goal", "title": "Savings target", "target_cents": 60000,
                     "current_saved_cents": 30000, "target_date": deadline.isoformat(), "contribution_cents": 10000}}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-plan", type=Path, help="Write a synthetic dated plan for owner API setup.")
    args = parser.parse_args()
    spec = sample_plan()
    if args.write_plan:
        args.write_plan.write_text(json.dumps(spec, indent=2) + "\n")
    print("SIMULATION: synthetic products; deterministic tool callers; no PayPal payments.")
    budget = 35_000
    requests = [("agent-a", "mic-standard", 22_000), ("agent-b", "vacuum-standard", 18_000)]
    baseline = [amount <= budget for _, _, amount in requests]
    print(json.dumps({"baseline": "independent_per_request_checks",
                      "available_cents": budget, "individually_allowed": baseline,
                      "combined_cents": sum(amount for _, _, amount in requests),
                      "exceeds_budget_by_cents": 5_000}, indent=2))
    with tempfile.TemporaryDirectory() as directory:
        ledger = Ledger(Path(directory) / "ledger.sqlite")
        ledger.create_household("demo-home", 0, 0)
        gateway = Gateway(ledger, Catalog(), require_plan=True)
        owner = Principal("demo-home", "owner", "owner")
        preview = gateway.plan(owner, "preview", {"plan": spec, "mode": "activate"})
        confirmed = gateway.plan(owner, "confirm", {"plan": spec, "mode": "activate", "preview_hash": preview["preview_hash"]})
        print(json.dumps({"owner_confirmed_plan": confirmed,
                          "explanation": "$600 cash minus $100 bill, $50 buffer and $100 savings contribution leaves $350. Expected $400 income affects only the forecast."}, indent=2))
        def submit(request):
            agent, sku, _ = request
            return gateway.propose(Principal("demo-home", agent, "agent"), {
                "request_key": agent + "-request", "items": [{"sku": sku, "quantity": 1}]})
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, requests))
        print(json.dumps({"goalguard": results, "budget": ledger.summary("demo-home")}, indent=2))
        denied_index = next(i for i, result in enumerate(results) if result["decision"] == "denied")
        denied = results[denied_index]
        agent = requests[denied_index][0]
        offer = denied["counteroffers"][0]
        recovery = gateway.propose(Principal("demo-home", agent, "agent"), {
            "request_key": agent + "-counteroffer",
            "items": [{"sku": i["sku"], "quantity": i["quantity"]} for i in offer["cart"]["items"]]})
        print(json.dumps({"accepted_counteroffer": recovery,
                          "remaining_budget": ledger.summary("demo-home")}, indent=2))
        purchase = recovery["purchase"]
        approved = gateway.approve(owner, purchase["id"], purchase["cart_hash"])
        # Do not print the bearer-like consent permit.
        print(json.dumps({"owner_approved": approved["state"],
                          "audit": ledger.audit(purchase["id"]),
                          "next_step": "Use the owner API for real sandbox checkout. This local demo makes no payment or LLM calls."}, indent=2))


if __name__ == "__main__":
    main()
