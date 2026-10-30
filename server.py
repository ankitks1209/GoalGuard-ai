"""Local prototype tool API, intentionally bound to loopback only."""

import argparse
import hashlib
import hmac
from http.cookies import CookieError, SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import secrets
import tempfile
import threading
from urllib.parse import unquote, urlparse

from goalguard import Ledger, Rejection
from goalguard.catalog import Catalog
from goalguard.config import sandbox_config, SANDBOX_KEYS
from goalguard.gateway import Gateway, Principal
from goalguard.paypal import PayPal, PaymentUnavailable
from goalguard.agent_view import agent_view
from goalguard.drafting import PlanDrafter
from goalguard.models import Gemini, ModelUnavailable, model_config
from goalguard.sessions import COOKIE_NAME, OwnerSession, OwnerSessions, session_cookie


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


def make_handler(gateway: Gateway, tokens: dict, *, static_root: Path | None = None):
    known = [(hashlib.sha256(token.encode()).digest(),
              Principal("demo-home", role, "owner" if role == "owner" else "agent"))
             for role, token in tokens.items()]
    sessions = OwnerSessions()
    assets = (static_root or Path(__file__).resolve().parent / "frontend" / "dist").resolve()

    class Handler(BaseHTTPRequestHandler):
        server_version = "GoalGuardPrototype/0.1"
        owner_session: OwnerSession | None = None
        response_cookie: str | None = None

        def log_message(self, fmt, *args):
            # Avoid recording raw URLs, bearer tokens, bodies or query parameters.
            pass

        def _header(self, name):
            values = self.headers.get_all(name, [])
            if len(values) > 1:
                raise Rejection("forbidden", "Ambiguous request headers.")
            return values[0] if values else ""

        def _bearer_actor(self):
            header = self._header("Authorization")
            if not header.startswith("Bearer "):
                raise Rejection("unauthorized", "A scoped bearer token is required.")
            fingerprint = hashlib.sha256(header[7:].encode()).digest()
            for expected, principal in known:
                if hmac.compare_digest(fingerprint, expected):
                    return principal
            raise Rejection("unauthorized", "Unknown token.")

        def _session_id(self):
            cookie = SimpleCookie()
            try:
                cookie.load(self._header("Cookie"))
            except CookieError:
                return ""
            morsel = cookie.get(COOKIE_NAME)
            return morsel.value if morsel is not None else ""

        def _browser_request(self, *, mutation):
            # Derive authority from the bound listener, never from forwarded headers.
            address = self.server.server_address
            if not isinstance(address, tuple) or address[0] != "127.0.0.1":
                raise Rejection("forbidden", "Browser sessions require the local IPv4 listener.")
            port = address[1]
            suffix = "" if port == 80 else f":{port}"
            host = self._header("Host")
            if host not in {"127.0.0.1" + suffix, "localhost" + suffix}:
                raise Rejection("forbidden", "Unexpected browser Host.")
            origin = self._header("Origin")
            if (mutation or origin) and origin != "http://" + host:
                raise Rejection("forbidden", "A same-origin browser request is required.")
            fetch_site = self._header("Sec-Fetch-Site")
            if fetch_site and fetch_site != "same-origin":
                raise Rejection("forbidden", "A same-origin browser request is required.")
            if mutation and self._header("Content-Type").split(";", 1)[0].strip().lower() != "application/json":
                raise Rejection("forbidden", "Browser mutations require application/json.")

        def _actor(self, method):
            if self._header("Authorization"):
                # CLI/agent bearer clients remain supported. Browser mutations use
                # the cookie path so bearer credentials cannot bypass CSRF checks.
                if method == "POST" and any(name in self.headers for name in
                                            ("Origin", "Sec-Fetch-Site", "Cookie")):
                    raise Rejection("forbidden", "Unlock a browser session before making changes.")
                return self._bearer_actor()
            session = sessions.get(self._session_id())
            self._browser_request(mutation=method == "POST")
            if method == "POST":
                sessions.check_csrf(session, self._header("X-CSRF-Token"))
            self.owner_session = session
            return session.principal

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
            principal = getattr(self, "principal", None)
            if principal is None or principal.role != "owner":
                payload = agent_view(payload)
            body = json.dumps(payload).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            if self.response_cookie is not None:
                self.send_header("Set-Cookie", self.response_cookie)
            self.end_headers()
            self.wfile.write(body)

        def _static(self, path):
            relative = "index.html" if path == "/" else unquote(path).lstrip("/")
            if relative != "index.html" and not relative.startswith("assets/"):
                raise Rejection("not_found", "Unknown interface asset.")
            target = (assets / relative).resolve()
            if not target.is_relative_to(assets) or not target.is_file():
                raise Rejection("not_found", "Build the owner interface before opening it.")
            body = target.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(body)

        def _dispatch(self, method):
            self.principal = None
            self.owner_session = None
            self.response_cookie = None
            try:
                path = urlparse(self.path).path.rstrip("/")
                if method == "GET" and not path.startswith("/v1/"):
                    self._static(path or "/")
                    return
                if method == "POST" and path == "/v1/owner/session":
                    self.principal = self._bearer_actor()
                    if self.principal.role != "owner":
                        raise Rejection("forbidden", "Only an owner can unlock the interface.")
                    self._browser_request(mutation=True)
                    if self._body():
                        raise Rejection("invalid_body", "Session exchange requires an empty JSON object.")
                    sessions.revoke(self._session_id())
                    session = sessions.create(self.principal)
                    self.response_cookie = session_cookie(session.identifier)
                    self._reply(200, sessions.describe(session))
                    return
                principal = self._actor(method)
                self.principal = principal
                if path == "/v1/owner/overview" and method == "GET":
                    result = gateway.owner_overview(principal)
                elif path == "/v1/owner/session" and method == "GET":
                    if self.owner_session is None:
                        raise Rejection("unauthorized", "An owner browser session is required.")
                    result = sessions.describe(self.owner_session)
                elif path == "/v1/owner/logout" and method == "POST":
                    if self.owner_session is None:
                        raise Rejection("unauthorized", "An owner browser session is required.")
                    if self._body():
                        raise Rejection("invalid_body", "Logout requires an empty JSON object.")
                    sessions.revoke(self.owner_session.identifier)
                    self.response_cookie = session_cookie("", clear=True)
                    result = {"status": "locked"}
                elif method == "GET" and path == "/v1/catalog":
                    result = {"products": gateway.catalog.public(), "simulation": "synthetic_catalog"}
                elif method == "GET" and path == "/v1/budget":
                    result = gateway.budget(principal)
                elif method == "POST" and path == "/v1/proposals":
                    result = gateway.propose(principal, self._body())
                elif path == "/v1/plan" and method == "GET":
                    result = gateway.plan(principal)
                elif path == "/v1/plan/audit" and method == "GET":
                    result = gateway.plan(principal, "audit")
                elif path in ("/v1/plan/draft", "/v1/plan/preview", "/v1/plan/confirm", "/v1/plan/cash-events") and method == "POST":
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
            except ModelUnavailable as error:
                self._reply(503, {"reason": error.code, "manual_entry_available": True,
                                  "message": "Model drafting did not complete. Manual plan entry remains available."})
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
    parser.add_argument("--model-env-file", type=Path, default=project / ".env.models")
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
    drafter = None
    try:
        models = model_config(args.model_env_file)
        if models["GEMINI_API_KEY"] and models["GEMINI_MODEL_B"]:
            drafter = PlanDrafter(Gemini(models["GEMINI_API_KEY"], models["GEMINI_MODEL_B"]))
    except (ValueError, OSError):
        print("Plan drafting configuration unavailable; manual plan entry remains available.")
    gateway = Gateway(ledger, Catalog(), paypal, require_plan=True, drafter=drafter)
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
    print("Owner text drafting: " + ("configured; explicit model-processing consent required" if drafter else "unavailable; use manual entry"))
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
