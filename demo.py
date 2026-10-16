"""Failure-first local demo. No LLM calls or PayPal payment requests."""

from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import tempfile

from goalguard import Ledger
from goalguard.catalog import Catalog
from goalguard.gateway import Gateway, Principal


def main():
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
        ledger.create_household("demo-home", 60_000, 25_000)
        gateway = Gateway(ledger, Catalog())
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
        owner = Principal("demo-home", "owner", "owner")
        purchase = recovery["purchase"]
        approved = gateway.approve(owner, purchase["id"], purchase["cart_hash"])
        # Do not print the bearer-like consent permit.
        print(json.dumps({"owner_approved": approved["state"],
                          "audit": ledger.audit(purchase["id"]),
                          "next_step": "Configure sandbox and complete real buyer checkout."}, indent=2))


if __name__ == "__main__":
    main()
