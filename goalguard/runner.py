"""Trusted, bounded tool dispatcher; no model provider or payment authority."""

import uuid

from .agent_view import agent_view
from .ledger import Rejection


class ProposalRunner:
    """One initial proposal plus one revision. A fresh run cannot reset gateway quotas."""

    def __init__(self, gateway, principal, *, skills=None):
        if principal.role != "agent":
            raise ValueError("Shopping runs require an agent principal.")
        self.gateway = gateway
        self.principal = principal
        self.tool_calls = 0
        self.proposals = 0
        self._hash = None
        self._key = None
        self._outcome = None
        self._stop_reason = None
        self._skills = dict(skills or {})

    @property
    def stop_reason(self):
        return self._stop_reason or ("tool_limit" if self.tool_calls >= 8 else None)

    def call(self, tool, arguments):
        if self.tool_calls >= 8:
            raise Rejection("tool_limit", "Tool budget exhausted.")
        self.tool_calls += 1
        if self._stop_reason:
            raise Rejection(self._stop_reason, "The run has stopped.")
        if not isinstance(arguments, dict):
            return agent_view({"reason": "invalid_body"})
        try:
            if tool == "get_skill" and set(arguments) == {"resource"}:
                resource = arguments["resource"]
                if isinstance(resource, str) and resource in self._skills:
                    return {"resource": resource, "text": self._skills[resource]}
                return agent_view({"reason": "invalid_request"})
            if tool == "get_catalog" and not arguments:
                return agent_view({"products": self.gateway.catalog.public()})
            if tool == "get_purchase" and set(arguments) == {"purchase_id"}:
                return self.gateway.inspect(self.principal, arguments["purchase_id"])
            if tool != "propose_purchase" or set(arguments) != {"items"}:
                return agent_view({"reason": "invalid_proposal"})
            cart_hash = self.gateway.catalog.quote(arguments["items"]).cart_hash
            retry = self._outcome == "unknown" and cart_hash == self._hash
            if self._outcome == "unknown" and not retry:
                self._stop_reason = "outcome_unknown"
                raise Rejection("outcome_unknown", "Inspect an uncertain result before changing the cart.")
            if not retry:
                if cart_hash == self._hash:
                    return agent_view({"reason": "invalid_proposal"})
                if self.proposals >= 2:
                    self._stop_reason = "revision_limit"
                    raise Rejection("revision_limit", "One revision is allowed.")
                self.proposals += 1
                self._hash = cart_hash
                self._key = str(uuid.uuid4())
            self._outcome = "unknown"  # Persist this key in memory before dispatch.
            try:
                result = self.gateway.propose(self.principal, {"items": arguments["items"],
                                                              "request_key": self._key})
            except (TimeoutError, ConnectionError):
                # Only an identical transport retry may reuse this in-flight key.
                return {"decision": "pending", "reason": "outcome_unknown"}
            self._outcome = result["decision"]
            if self._outcome != "denied":
                self._stop_reason = "run_complete"
            elif self.proposals == 2:
                self._stop_reason = "revision_limit"
            return agent_view(result)
        except Rejection as error:
            if error.code in {"revision_limit", "outcome_unknown"}:
                raise
            self._outcome = "denied"
            if self.proposals >= 2:
                self._stop_reason = "revision_limit"
            return agent_view(error.as_dict())
        except Exception:
            self._stop_reason = "internal_error"
            return agent_view({"reason": "internal_error"})
