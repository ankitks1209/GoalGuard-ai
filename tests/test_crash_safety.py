import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

from goalguard import Ledger, Rejection
from goalguard.catalog import Catalog
from goalguard.gateway import Gateway, Principal
from tests.test_gateway import FakePayPal


class CrashSafetyTests(unittest.TestCase):
    def run_crash(self, action, expected):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            ledger = Ledger(folder / "ledger.sqlite")
            ledger.create_household("demo-home", 60_000, 25_000)
            paypal = FakePayPal()
            gateway = Gateway(ledger, Catalog(), paypal)
            owner = Principal("demo-home", "owner", "owner")
            proposal = gateway.propose(Principal("demo-home", "agent-a", "agent"), {
                "items": [{"sku": "mic-standard", "quantity": 1}], "request_key": "crash-check"})["purchase"]
            approved = gateway.approve(owner, proposal["id"], proposal["cart_hash"])
            gateway.checkout(owner, proposal["id"])
            paypal.order["status"] = "APPROVED"
            if action != "authorize":
                gateway.execute(owner, approved["id"], "authorize", approved["permit"])
            (folder / "provider.json").write_text(json.dumps({"order": paypal.order,
                                                             "authorization": paypal.authorization}))
            (folder / "request.json").write_text(json.dumps({"purchase": approved["id"],
                                                            "action": action, "permit": approved["permit"]}))
            process = subprocess.Popen([sys.executable, "-m", "tests.crash_worker", directory],
                                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic() + 10
                while not (folder / "ready").exists() and process.poll() is None and time.monotonic() < deadline:
                    time.sleep(0.01)
                self.assertTrue((folder / "ready").exists(), "Child did not reach the explicit crash barrier.")
                process.kill()  # Only the test-owned subprocess, after its barrier.
                process.communicate(timeout=3)
            finally:
                if process.poll() is None:
                    process.kill()
                    process.communicate(timeout=3)
            restarted = Ledger(folder / "ledger.sqlite")
            pending = restarted.get(approved["id"])
            self.assertEqual(pending["state"], {"authorize": "authorizing", "capture": "capturing", "void": "voiding"}[action])
            self.assertEqual(restarted.summary("demo-home")["available_cents"], 13_000)
            with self.assertRaises(Rejection):
                restarted.release(approved["id"])
            operation_id = next(event["details"]["operation_id"] for event in reversed(restarted.audit(approved["id"]))
                                if event["event"] == pending["state"])
            intent = json.loads(restarted.operation(operation_id)["intent_json"])
            self.assertEqual(intent["amount_cents"], 22_000)
            self.assertEqual(intent["cart_hash"], approved["cart_hash"])
            provider_state = json.loads((folder / "provider.json").read_text())
            self.assertEqual(provider_state["request_id"], operation_id)
            recovery_provider = FakePayPal()
            recovery_provider.order = provider_state["order"]
            recovery_provider.authorization = provider_state["authorization"]
            recovery = Gateway(restarted, Catalog(), recovery_provider)
            self.assertEqual(recovery.refresh(owner, approved["id"], operation_id)["state"], expected)
            self.assertFalse(any(call[0] == "POST" for call in recovery_provider.calls))
            self.assertEqual(restarted.summary("demo-home")["available_cents"], 35_000 if action == "void" else 13_000)

    def test_kill_after_simulated_authorization_before_ledger_completion(self):
        self.run_crash("authorize", "authorized")

    def test_kill_after_simulated_capture_before_ledger_completion(self):
        self.run_crash("capture", "captured")

    def test_kill_after_simulated_void_before_ledger_completion(self):
        self.run_crash("void", "voided")
