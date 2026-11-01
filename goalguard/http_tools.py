"""Agent-only loopback transport for the existing bounded proposal dispatcher."""

from dataclasses import dataclass
import hashlib
from http.client import HTTPException
import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .agent_view import agent_view
from .ledger import Rejection


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


@dataclass(frozen=True)
class ProposalFingerprint:
    # Local retry identity only. This is NOT the gateway's consent/cart hash.
    cart_hash: str


class RemoteCatalog:
    def __init__(self, transport):
        self.transport = transport

    def public(self):
        result = self.transport.request("GET", "/v1/catalog")
        if not isinstance(result.get("products"), list):
            raise Rejection("request_rejected", "Catalog unavailable.")
        return agent_view(result)["products"]

    def quote(self, items):
        # Validate the proposal shape, never calculate prices locally.
        if not isinstance(items, list) or not 1 <= len(items) <= 10:
            raise Rejection("invalid_cart", "Provide one to ten items.")
        for item in items:
            if (not isinstance(item, dict) or set(item) != {"sku", "quantity"}
                    or not isinstance(item["sku"], str) or not 1 <= len(item["sku"]) <= 128
                    or type(item["quantity"]) is not int or not 1 <= item["quantity"] <= 100):
                raise Rejection("invalid_cart", "Provide only SKU and integer quantity.")
        encoded = json.dumps(items, sort_keys=True, separators=(",", ":")).encode()
        return ProposalFingerprint(hashlib.sha256(encoded).hexdigest())


class ScopedHTTPGateway:
    """No owner methods, arbitrary URLs, redirects, proxies or payment credentials.

    The host receives one agent token; the model receives neither this object nor
    the token. Catalog prices and purchase authority remain on the API server.
    """

    def __init__(self, agent, token, *, port=8765, timeout=15):
        if agent not in {"agent-a", "agent-b"}:
            raise ValueError("Use agent-a or agent-b.")
        if not isinstance(token, str) or len(token) < 32 or any(c.isspace() for c in token):
            raise ValueError("Invalid agent credential; its value was not logged.")
        if type(port) is not int or not 1 <= port <= 65535:
            raise ValueError("Invalid loopback port.")
        self.agent = agent
        self._token = token
        self._base = f"http://127.0.0.1:{port}"
        self._timeout = timeout
        self._opener = build_opener(ProxyHandler({}), NoRedirect())
        self.catalog = RemoteCatalog(self)

    def request(self, method, path, body=None):
        allowed = ((method == "GET" and path == "/v1/catalog")
                   or (method == "POST" and path == "/v1/proposals")
                   or (method == "GET" and path.startswith("/v1/purchases/")
                       and len(path.split("/")) == 4))
        if not allowed:
            raise Rejection("forbidden", "Not an agent tool route.")
        data = json.dumps(body, allow_nan=False).encode() if body is not None else None
        request = Request(self._base + path, data=data, method=method,
                          headers={"Authorization": "Bearer " + self._token,
                                   "Content-Type": "application/json"})
        try:
            response = self._opener.open(request, timeout=self._timeout)
        except HTTPError as error:
            response = error
        except (URLError, TimeoutError, OSError, HTTPException):
            raise ConnectionError("Agent API unavailable; credential not logged.") from None
        try:
            with response:
                status = response.code
                raw = response.read(262_145)
        except (OSError, HTTPException):
            raise ConnectionError("Agent API response lost; preserve the request key.") from None
        # A write may have committed even when its HTTP response was lost/broken.
        if status >= 500 or len(raw) > 262_144:
            raise TimeoutError("Agent API outcome unavailable; preserve the request key.")
        try:
            result = json.loads(raw)
            if not isinstance(result, dict):
                raise ValueError
            if status >= 300 and "reason" not in result:
                raise ValueError
            if path == "/v1/catalog" and "reason" not in result and (
                    not isinstance(result.get("products"), list)
                    or any(not isinstance(item, dict) for item in result["products"])):
                raise ValueError
            if path == "/v1/proposals" and "purchase" not in result and "reason" not in result:
                # Projection must not turn an uncertain/malformed write result
                # into a definite denial and permit a new cart/request identity.
                raise ValueError
            return agent_view(result)
        except (ValueError, TypeError, KeyError):
            raise TimeoutError("Agent API response unavailable; preserve the request key.") from None

    def _check_principal(self, principal):
        if principal.role != "agent" or principal.identity != self.agent:
            raise Rejection("forbidden", "Agent scope mismatch.")

    def propose(self, principal, body):
        self._check_principal(principal)
        result = self.request("POST", "/v1/proposals", body)
        if result.get("decision") not in {"reserved", "denied"}:
            raise TimeoutError("Proposal outcome unavailable; preserve the request key.")
        return result

    def inspect(self, principal, purchase_id):
        self._check_principal(principal)
        if (not isinstance(purchase_id, str) or not 1 <= len(purchase_id) <= 128
                or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for c in purchase_id)):
            raise Rejection("invalid_request", "Invalid purchase ID.")
        return self.request("GET", "/v1/purchases/" + quote(purchase_id, safe=""))
