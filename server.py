"""Local prototype tool API, intentionally bound to loopback only."""

import argparse
import hashlib
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import tempfile
import threading
from urllib.parse import urlparse

from goalguard import Ledger, Rejection
from goalguard.catalog import Catalog
from goalguard.config import sandbox_config, SANDBOX_KEYS
from goalguard.gateway import Gateway, Principal
from goalguard.paypal import PayPal, PaymentUnavailable
from goalguard.agent_view import agent_view


def token_config(path: Path):
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        body = {role: secrets.token_urlsafe(32) for role in ("owner", "agent-a", "agent-b")}
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as file:
            json.dump(body, file, indent=2)
    body = json.loads(path.read_text())
    if set(body) != {"owner", "agent-a", "agent-b"} or any(
            not isinstance(token, str) or len(token) < 32 for token in body.values()):
        raise ValueError("Invalid local token configuration")
    if len(set(body.values())) != 3:
        raise ValueError("Owner and agent tokens must differ")
    return body


def make_handler(gateway: Gateway, tokens: dict):
    known = [(hashlib.sha256(token.encode()).digest(),
              Principal("demo-home", role, "owner" if role == "owner" else "agent"))
             for role, token in tokens.items()]

    class Handler(BaseHTTPRequestHandler):
        server_version = "GoalGuardPrototype/0.1"

        def log_message(self, fmt, *args):
            # Avoid recording raw URLs, bearer tokens, bodies or query parameters.
            pass

        def _actor(self):
            header = self.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                raise Rejection("unauthorized", "A scoped bearer token is required.")
            fingerprint = hashlib.sha256(header[7:].encode()).digest()
            for expected, principal in known:
                if hmac.compare_digest(fingerprint, expected):
                    return principal
            raise Rejection("unauthorized", "Unknown token.")

        def _body(self):
            raw_length = self.headers.get("Content-Length", "0")
            try:
                length = int(raw_length)
            except ValueError:
                raise Rejection("invalid_body", "Invalid content length.") from None
            if length < 0 or length > 32_768:
                raise Rejection("invalid_body", "JSON body must be at most 32 KB.")
            try:
                value = json.loads(self.rfile.read(length)) if length else {}
            except (ValueError, UnicodeDecodeError):
                raise Rejection("invalid_body", "A JSON object is required.") from None
            if not isinstance(value, dict):
                raise Rejection("invalid_body", "A JSON object is required.")
            return value

        def _reply(self, code, payload):
            if getattr(self, "principal", None) is None or self.principal.role != "owner":
                payload = agent_view(payload)
            body = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _dispatch(self, method):
            self.principal = None
            try:
                principal = self._actor()
                self.principal = principal
                path = urlparse(self.path).path.rstrip("/")
                if method == "GET" and path == "/v1/catalog":
                    result = {"products": gateway.catalog.public(), "simulation": "synthetic_catalog"}
                elif method == "GET" and path == "/v1/budget":
                    result = gateway.budget(principal)
                elif method == "POST" and path == "/v1/proposals":
                    result = gateway.propose(principal, self._body())
                elif path == "/v1/plan" and method == "GET":
                    result = gateway.plan(principal)
                elif path == "/v1/plan/audit" and method == "GET":
                    result = gateway.plan(principal, "audit")
                elif path in ("/v1/plan/preview", "/v1/plan/confirm", "/v1/plan/cash-events") and method == "POST":
                    result = gateway.plan(principal, path.rsplit("/", 1)[-1], self._body())
                elif path.startswith("/v1/purchases/"):
                    parts = path.split("/")
                    purchase = parts[3]
                    action = parts[4] if len(parts) == 5 else None
                    if len(parts) > 5:
                        raise Rejection("not_found", "Unknown endpoint.")
                    if method == "GET" and action is None:
                        result = gateway.inspect(principal, purchase)
                    elif method == "GET" and action == "audit":
                        result = gateway.audit(principal, purchase)
                    elif method == "POST":
                        body = self._body()
                        fields = {"approve": {"cart_hash"}, "release": set(), "checkout": set(),
                                  "authorize": {"permit"}, "capture": {"permit"}, "void": {"permit"},
                                  "refresh": {"operation_id"}}
                        if action not in fields or set(body) != fields[action]:
                            raise Rejection("invalid_body", "Invalid action or unexpected fields.")
                        if action == "approve":
                            result = gateway.approve(principal, purchase, body["cart_hash"])
                        elif action == "release":
                            result = gateway.release(principal, purchase)
                        elif action == "checkout":
                            result = gateway.checkout(principal, purchase)
                        elif action == "refresh":
                            result = gateway.refresh(principal, purchase, body["operation_id"])
                        else:
                            result = gateway.execute(principal, purchase, action, body["permit"])
                    else:
                        raise Rejection("not_found", "Unknown endpoint.")
                else:
                    raise Rejection("not_found", "Unknown endpoint.")
                self._reply(200, result)
            except Rejection as error:
                code = {"unauthorized": 401, "forbidden": 403, "not_found": 404,
                        "unknown_purchase": 404, "unknown_operation": 404}.get(error.code, 409)
                self._reply(code, error.as_dict())
            except PaymentUnavailable as error:
                self._reply(503, {"reason": "payment_unavailable", "message": str(error)})
            except Exception:
                self._reply(500, {"reason": "internal_error", "message": "Operation failed; inspect purchase status before retrying."})

        def do_GET(self):
            self._dispatch("GET")

        def do_POST(self):
            self._dispatch("POST")

    return Handler


def main():
    parser = argparse.ArgumentParser()
    project = Path(__file__).resolve().parent
    default_state = Path(tempfile.gettempdir()) / (
        "goalguard-runtime-" + hashlib.sha256(str(project).encode()).hexdigest()[:12])
    parser.add_argument("--state-dir", type=Path, default=default_state)
    parser.add_argument("--env-file", type=Path, default=project / ".env")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    if args.state_dir.resolve().is_relative_to(project):
        parser.error("State directory must be outside the source repository; use ../../work/goalguard-runtime.")
    args.state_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    ledger = Ledger(args.state_dir / "ledger.sqlite")
    try:
        ledger.summary("demo-home")
    except Rejection as error:
        if error.code != "unknown_household":
            raise
        ledger.create_household("demo-home", 0, 0)
    tokens = token_config(args.state_dir / "tokens.json")
    paypal = None
    config = sandbox_config(args.env_file)
    if all(config[key] for key in SANDBOX_KEYS):
        paypal = PayPal(*(config[key] for key in SANDBOX_KEYS))
    gateway = Gateway(ledger, Catalog(), paypal, require_plan=True)
    server = ThreadingHTTPServer(("127.0.0.1", args.port), make_handler(gateway, tokens))
    stop = threading.Event()
    def sweep():
        while not stop.wait(5):
            ledger.sweep("demo-home")
    sweeper = threading.Thread(target=sweep, daemon=True)
    sweeper.start()
    print(f"GoalGuard API: http://127.0.0.1:{server.server_port}")
    print(f"Scoped tokens stored locally in {args.state_dir / 'tokens.json'}; never give owner token to a model.")
    print("Catalog: synthetic. Fulfilment: manual demo action. PayPal: " +
          ("sandbox adapter configured; consult saved verification evidence" if paypal else "not configured"))
    print("Purchasing requires an owner-confirmed current financial plan; no plan is activated automatically.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        stop.set()
        server.server_close()
        sweeper.join(timeout=6)


if __name__ == "__main__":
    main()
