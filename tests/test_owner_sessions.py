"""Synthetic owner-browser authentication through the real HTTP handler."""

import io
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from goalguard import Ledger
from goalguard.catalog import Catalog
from goalguard.gateway import Gateway
from server import make_handler
from test_gateway import FakePayPal


class OwnerSessionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger = Ledger(Path(self.tmp.name) / "ledger.sqlite")
        self.ledger.create_household("demo-home", 60_000, 25_000)
        self.gateway = Gateway(self.ledger, Catalog())
        self.tokens = {"owner": "fixture-owner-" + "x" * 32,
                       "agent-a": "fixture-agent-" + "x" * 32}
        self.handler = make_handler(self.gateway, self.tokens)
        self.origin = "http://127.0.0.1:8765"

    def call(self, path, body=None, *, headers=None, handler=None):
        payload = json.dumps(body).encode() if body is not None else b""
        method = "POST" if body is not None else "GET"
        fields = {"Host": "127.0.0.1:8765", "Content-Type": "application/json",
                  "Content-Length": str(len(payload)), **(headers or {})}
        raw = (f"{method} {path} HTTP/1.0\r\n" + "\r\n".join(
            f"{key}: {value}" for key, value in fields.items()) + "\r\n\r\n").encode() + payload

        class Connection:
            def __init__(self):
                self.response = bytearray()

            def makefile(self, *args):
                return io.BytesIO(raw)

            def sendall(self, value):
                self.response.extend(value)

        connection = Connection()
        (handler or self.handler)(connection, ("127.0.0.1", 12345),
                                  SimpleNamespace(server_address=("127.0.0.1", 8765)))
        head, content = bytes(connection.response).split(b"\r\n\r\n", 1)
        lines = head.decode().split("\r\n")
        response_headers = dict(line.split(": ", 1) for line in lines[1:])
        value = json.loads(content) if response_headers.get("Content-Type") == "application/json" else content.decode()
        return int(lines[0].split()[1]), value, response_headers

    def unlock(self, role="owner", **headers):
        return self.call("/v1/owner/session", {}, headers={
            "Authorization": "Bearer " + self.tokens[role], "Origin": self.origin, **headers})

    def browser(self):
        code, body, headers = self.unlock()
        self.assertEqual(code, 200)
        return {"Cookie": headers["Set-Cookie"].split(";", 1)[0],
                "X-CSRF-Token": body["csrf_token"], "Origin": self.origin}

    def proposal(self):
        code, body, _ = self.call("/v1/proposals", {
            "items": [{"sku": "mic-standard", "quantity": 1}], "request_key": "session-test"},
            headers={"Authorization": "Bearer " + self.tokens["agent-a"]})
        self.assertEqual(code, 200)
        return body["purchase"]

    def test_owner_token_exchanges_for_opaque_cookie_and_csrf(self):
        code, body, headers = self.unlock()
        self.assertEqual(code, 200)
        self.assertEqual(body["expires_in_seconds"], 1800)
        self.assertGreaterEqual(len(body["csrf_token"]), 32)
        cookie = headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)
        self.assertIn("Path=/", cookie)
        self.assertIn("Max-Age=1800", cookie)
        self.assertNotIn(self.tokens["owner"], json.dumps(body) + cookie)
        self.assertEqual(headers["Cache-Control"], "no-store")
        code, status, _ = self.call("/v1/owner/session", headers={"Cookie": cookie.split(";", 1)[0]})
        self.assertEqual(code, 200)
        self.assertEqual(status["csrf_token"], body["csrf_token"])

    def test_owner_overview_lists_only_this_households_purchases_and_events(self):
        purchase = self.proposal()
        self.ledger.create_household("other-home", 60_000, 25_000)
        from goalguard.gateway import Principal
        outsider = self.gateway.propose(Principal("other-home", "outside-agent", "agent"), {
            "items": [{"sku": "mic-standard", "quantity": 1}], "request_key": "outside"})["purchase"]
        code, body, _ = self.call("/v1/owner/overview", headers=self.browser())
        self.assertEqual(code, 200)
        self.assertIsNone(body["plan"])
        self.assertEqual([item["id"] for item in body["purchases"]], [purchase["id"]])
        self.assertEqual(body["purchases"][0]["cart"]["items"][0]["sku"], "mic-standard")
        self.assertIn("reserved", [event["event"] for event in body["events"]])
        self.assertNotIn(outsider["id"], json.dumps(body))
        self.assertEqual(self.call("/v1/owner/overview", headers={
            "Authorization": "Bearer " + self.tokens["agent-a"]})[0], 403)
        self.assertEqual(self.call("/v1/owner/overview")[0], 401)

    def test_built_interface_is_public_but_source_and_credentials_are_not(self):
        root = Path(self.tmp.name) / "interface"
        root.mkdir()
        (root / "index.html").write_text('<div id="root"></div>')
        (root / "assets").mkdir()
        (root / "assets" / "app.js").write_text("/* fixture asset */")
        self.handler = make_handler(self.gateway, self.tokens, static_root=root)
        code, content, headers = self.call("/")
        self.assertEqual(code, 200)
        self.assertIn('<div id="root">', content)
        self.assertIn("text/html", headers["Content-Type"])
        self.assertEqual(self.call("/assets/app.js")[0], 200)
        for path in ("/.env", "/server.py", "/src/main.tsx", "/assets/../../server.py", "/%2e%2e/server.py"):
            self.assertNotEqual(self.call(path)[0], 200)

    def test_missing_invalid_and_agent_tokens_cannot_unlock(self):
        for headers, expected in [({}, 401), ({"Authorization": "Bearer invalid"}, 401),
                                  ({"Authorization": "Bearer " + self.tokens["agent-a"]}, 403)]:
            with self.subTest(headers=list(headers)):
                code, body, response = self.call("/v1/owner/session", {},
                                                headers={"Origin": self.origin, **headers})
                self.assertEqual(code, expected)
                self.assertNotIn("Set-Cookie", response)
                self.assertNotIn("csrf_token", body)

    def test_unlock_rejects_wrong_origin_host_content_type_and_payload(self):
        for extra in ({"Origin": "https://attacker.invalid"}, {"Origin": "null"},
                      {"Origin": ""}, {"Host": "attacker.invalid:8765"},
                      {"Origin": self.origin + "/"}, {"Host": "127.0.0.1:9999"},
                      {"Content-Type": "text/plain"}, {"Sec-Fetch-Site": "cross-site"}):
            with self.subTest(extra=extra):
                self.assertEqual(self.unlock(**extra)[0], 403)
        self.assertEqual(self.call("/v1/owner/session", {"owner": True}, headers={
            "Origin": self.origin, "Authorization": "Bearer " + self.tokens["owner"]})[0], 409)

    def test_cookie_reads_owner_data_but_missing_or_malformed_cookie_does_not(self):
        browser = self.browser()
        code, owner, _ = self.call("/v1/budget", headers=browser)
        self.assertEqual(code, 200)
        self.assertIn("available_cents", owner)
        for cookie in ("", "goalguard_owner_session=unknown", "goalguard_owner_session=\"unterminated"):
            self.assertEqual(self.call("/v1/budget", headers={"Cookie": cookie})[0], 401)
        self.assertEqual(self.call("/v1/budget", headers={**browser, "Host": "attacker.invalid"})[0], 403)

    def test_expiry_at_30_minutes_does_not_extend_on_read_or_release_reservation(self):
        purchase = self.proposal()
        with patch("time.monotonic", return_value=100):
            browser = self.browser()
        with patch("time.monotonic", return_value=1899):
            code, body, _ = self.call("/v1/owner/session", headers=browser)
            self.assertEqual(code, 200)
            self.assertEqual(body["expires_in_seconds"], 1)
        with patch("time.monotonic", return_value=1900):
            self.assertEqual(self.call("/v1/budget", headers=browser)[0], 401)
            self.assertEqual(self.call(f"/v1/purchases/{purchase['id']}/release", {}, headers=browser)[0], 401)
        self.assertEqual(self.ledger.get(purchase["id"])["state"], "reserved")

    def test_logout_revokes_cookie_and_does_not_release_reservation(self):
        purchase = self.proposal()
        browser = self.browser()
        code, _, response = self.call("/v1/owner/logout", {}, headers=browser)
        self.assertEqual(code, 200)
        self.assertIn("Max-Age=0", response["Set-Cookie"])
        self.assertEqual(self.call("/v1/budget", headers=browser)[0], 401)
        self.assertEqual(self.ledger.get(purchase["id"])["state"], "reserved")

    def test_restart_invalidates_session_but_preserves_ledger(self):
        purchase = self.proposal()
        browser = self.browser()
        restarted = make_handler(self.gateway, self.tokens)
        self.assertEqual(self.call("/v1/budget", headers=browser, handler=restarted)[0], 401)
        self.assertEqual(self.ledger.get(purchase["id"])["state"], "reserved")

    def test_mutations_require_session_bound_csrf_and_expected_origin_host(self):
        purchase = self.proposal()
        browser = self.browser()
        other = self.browser()
        path = f"/v1/purchases/{purchase['id']}/release"
        for extra in ({"X-CSRF-Token": ""}, {"X-CSRF-Token": "incorrect"},
                      {"X-CSRF-Token": other["X-CSRF-Token"]}, {"Origin": ""},
                      {"Origin": "https://attacker.invalid"}, {"Host": "attacker.invalid"},
                      {"Content-Type": "text/plain"}, {"Sec-Fetch-Site": "cross-site"}):
            with self.subTest(extra=extra):
                self.assertEqual(self.call(path, {}, headers={**browser, **extra})[0], 403)
                self.assertEqual(self.ledger.get(purchase["id"])["state"], "reserved")
        self.assertEqual(self.call(path, {}, headers=browser)[0], 200)

    def test_logout_requires_csrf_and_does_not_revoke_other_sessions(self):
        browser, other = self.browser(), self.browser()
        self.assertEqual(self.call("/v1/owner/logout", {}, headers={**browser, "X-CSRF-Token": ""})[0], 403)
        self.assertEqual(self.call("/v1/budget", headers=browser)[0], 200)
        self.assertEqual(self.call("/v1/owner/logout", {}, headers=browser)[0], 200)
        self.assertEqual(self.call("/v1/budget", headers=other)[0], 200)

    def test_reunlock_rotates_presented_session_without_replaying_mutation(self):
        purchase = self.proposal()
        browser = self.browser()
        code, _, response = self.unlock(Cookie=browser["Cookie"])
        self.assertEqual(code, 200)
        self.assertNotEqual(response["Set-Cookie"].split(";", 1)[0], browser["Cookie"])
        self.assertEqual(self.call("/v1/budget", headers=browser)[0], 401)
        self.assertEqual(self.ledger.get(purchase["id"])["state"], "reserved")

    def test_browser_cannot_bypass_csrf_with_owner_bearer(self):
        purchase = self.proposal()
        path = f"/v1/purchases/{purchase['id']}/release"
        bearer = {"Authorization": "Bearer " + self.tokens["owner"]}
        for extra in ({"Origin": self.origin}, {"Sec-Fetch-Site": "same-origin"},
                      {"Cookie": "goalguard_owner_session=invalid"}):
            self.assertEqual(self.call(path, {}, headers={**bearer, **extra})[0], 403)
        self.assertEqual(self.ledger.get(purchase["id"])["state"], "reserved")
        self.assertEqual(self.call(path, {}, headers=bearer)[0], 200)

    def test_session_is_owner_only_and_exact_cart_consent_still_applies(self):
        purchase = self.proposal()
        browser = self.browser()
        path = f"/v1/purchases/{purchase['id']}"
        code, _, _ = self.call(path + "/approve", {"cart_hash": "changed"}, headers=browser)
        self.assertEqual(code, 409)
        self.assertEqual(self.ledger.get(purchase["id"])["state"], "reserved")
        code, approved, _ = self.call(path + "/approve", {"cart_hash": purchase["cart_hash"]}, headers=browser)
        self.assertEqual(code, 200)
        self.assertIn("permit", approved)
        self.assertEqual(self.call("/v1/proposals", {}, headers=browser)[0], 403)
        self.assertEqual(self.call(path + "/refresh", {"operation_id": "unknown"}, headers=browser)[0], 404)

    def test_uncertain_payment_survives_expiry_and_refresh_never_repeats_capture(self):
        paypal = FakePayPal()
        self.gateway.paypal = paypal
        purchase = self.proposal()
        path = f"/v1/purchases/{purchase['id']}"
        with patch("time.monotonic", return_value=100):
            browser = self.browser()
            code, approved, _ = self.call(path + "/approve", {"cart_hash": purchase["cart_hash"]}, headers=browser)
            self.assertEqual(code, 200)
            self.assertEqual(self.call(path + "/checkout", {}, headers=browser)[0], 200)
            paypal.order["status"] = "APPROVED"  # Synthetic buyer approval only.
            self.assertEqual(self.call(path + "/authorize", {"permit": approved["permit"]}, headers=browser)[0], 200)
            paypal.lose_capture_reply = True
            self.assertEqual(self.call(path + "/capture", {"permit": approved["permit"]}, headers=browser)[0], 503)
        operation = next(event["details"]["operation_id"] for event in self.ledger.audit(purchase["id"])
                         if event["event"] == "capturing")
        with patch("time.monotonic", return_value=1900):
            self.assertEqual(self.call(path + "/refresh", {"operation_id": operation}, headers=browser)[0], 401)
            self.assertEqual(self.ledger.get(purchase["id"])["state"], "reconcile_pending")
            renewed = self.browser()
            self.assertEqual(self.ledger.get(purchase["id"])["state"], "reconcile_pending")
            code, overview, _ = self.call("/v1/owner/overview", headers=renewed)
            self.assertEqual(code, 200)
            self.assertEqual(overview["purchases"][0]["operation_id"], operation)
            self.assertEqual(overview["purchases"][0]["permit"], approved["permit"])
            code, result, _ = self.call(path + "/refresh", {"operation_id": operation}, headers=renewed)
            self.assertEqual(code, 200)
            self.assertEqual(result["state"], "captured")
        self.assertEqual(sum(call[0] == "POST" and call[1].endswith("/capture") for call in paypal.calls), 1)


class HTTPTests(unittest.TestCase):
    def test_exchange_protected_mutation_and_logout_over_tcp(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite")
            ledger.create_household("demo-home", 60_000, 25_000)
            tokens = {"owner": "fixture-owner-" + "x" * 32}
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(Gateway(ledger, Catalog()), tokens))
            thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01))
            thread.start()
            origin = f"http://127.0.0.1:{server.server_port}"

            def call(path, body=None, headers=None):
                connection = HTTPConnection("127.0.0.1", server.server_port, timeout=3)
                try:
                    connection.request("POST" if body is not None else "GET", path,
                                       json.dumps(body) if body is not None else None,
                                       {"Content-Type": "application/json", **(headers or {})})
                    response = connection.getresponse()
                    return response.status, json.load(response), dict(response.getheaders())
                finally:
                    connection.close()

            try:
                code, body, response = call("/v1/owner/session", {}, {
                    "Authorization": "Bearer " + tokens["owner"], "Origin": origin})
                self.assertEqual(code, 200)
                browser = {"Cookie": response["Set-Cookie"].split(";", 1)[0], "Origin": origin,
                           "X-CSRF-Token": body["csrf_token"]}
                self.assertEqual(call("/v1/budget", headers=browser)[0], 200)
                code, overview, _ = call("/v1/owner/overview", headers=browser)
                self.assertEqual(code, 200)
                self.assertEqual(overview["purchases"], [])
                self.assertEqual(call("/v1/owner/logout", {}, {**browser, "X-CSRF-Token": "wrong"})[0], 403)
                self.assertEqual(call("/v1/owner/logout", {}, browser)[0], 200)
                self.assertEqual(call("/v1/budget", headers=browser)[0], 401)
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
