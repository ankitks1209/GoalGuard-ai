from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from goalguard.gateway import Principal


class JudgingDemoTests(unittest.TestCase):
    def test_seed_protects_budget_and_leaves_exact_cart_consent_to_judge(self):
        from scripts.judging_demo import make_workspace

        with TemporaryDirectory() as directory:
            gateway = make_workspace(Path(directory))
            owner = Principal("demo-home", "owner", "owner")
            view = gateway.owner_overview(owner)
            plan = view["plan"]
            self.assertEqual(plan["protected_cents"], 25000)
            self.assertEqual(plan["available_cents"], 3000)
            self.assertEqual(plan["encumbered_cents"], 32000)
            self.assertEqual(plan["spent_cents"], 0)
            carts = {p["cart"]["items"][0]["sku"]: p for p in view["purchases"]}
            self.assertEqual(set(carts), {"mic-standard", "vacuum-budget"})
            for purchase in carts.values():
                self.assertEqual(purchase["state"], "reserved")
                self.assertIsNone(purchase["permit"])
            self.assertIsNone(gateway.paypal)
            self.assertIsNone(gateway.drafter)
            mic = carts["mic-standard"]
            approved = gateway.approve(owner, mic["id"], mic["cart_hash"])
            self.assertEqual(approved["state"], "approved")
            self.assertEqual(gateway.budget(owner)["spent_cents"], 0)
