from concurrent.futures import ThreadPoolExecutor
import json
from pathlib import Path
import sqlite3
import stat
import tempfile
import unittest

from goalguard import Cart, Item, Ledger
from goalguard.config import sandbox_config


class SecurityTests(unittest.TestCase):
    def test_signing_key_is_private_file_not_database_setting(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.sqlite"
            ledger = Ledger(path)
            self.assertEqual(stat.S_IMODE(ledger.signing_key_path.stat().st_mode), 0o600)
            with sqlite3.connect(path) as db:
                self.assertIsNone(db.execute("SELECT value FROM settings WHERE key='signing_key'").fetchone())

    def test_consent_consumption_and_intent_are_atomic(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "ledger.sqlite"
            ledger = Ledger(path)
            ledger.create_household("home", 60_000, 25_000)
            cart = Cart("merchant", (Item("mic", 1, 22_000),))
            purchase = ledger.reserve("home", "agent", cart, "one")
            approved = ledger.approve(purchase["id"], cart)
            def begin(_):
                try:
                    return ledger.begin_payment(purchase["id"], "authorize", approved["permit"], cart)["execute"]
                except Exception as error:
                    self.assertEqual(getattr(error, "code", None), "reconcile_required")
                    return False
            with ThreadPoolExecutor(max_workers=2) as pool:
                self.assertEqual(sum(pool.map(begin, range(2))), 1)
            with sqlite3.connect(path) as db:
                row = db.execute("SELECT state,permit_consumed_at FROM purchases WHERE id=?", (purchase["id"],)).fetchone()
                self.assertEqual(row[0], "authorizing")
                self.assertIsNotNone(row[1])
                operations = db.execute("SELECT intent_json FROM operations WHERE purchase=?", (purchase["id"],)).fetchall()
                self.assertEqual(len(operations), 1)
                self.assertEqual(json.loads(operations[0][0])["amount_cents"], 22_000)

    def test_env_file_has_no_shell_expansion(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("PAYPAL_SANDBOX_CLIENT_ID='$(not-a-command)'\n")
            from unittest.mock import patch
            with patch.dict("os.environ", {}, clear=True):
                self.assertEqual(sandbox_config(path)["PAYPAL_SANDBOX_CLIENT_ID"], "$(not-a-command)")

    def test_unknown_env_entry_is_rejected_without_echoing_value(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("UNSUPPORTED=fixture-sensitive-value\n")
            with self.assertRaises(ValueError) as error:
                sandbox_config(path)
            self.assertNotIn("fixture-sensitive-value", str(error.exception))
