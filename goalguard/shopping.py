"""Bounded real-model shopping loop around ProposalRunner, never owner authority."""

from datetime import datetime, timezone
import hashlib
import json
import time
import uuid

from .ledger import Rejection
from .models import ModelUnavailable


SKILL_DESCRIPTION = (
    "Available skill: propose-purchase — propose catalog purchases and recover "
    "from denials. Load it with get_skill when relevant. Its denial reference "
    "is a separate resource; load only when needed."
)
SKILL_TOOL = {
    "name": "get_skill",
    "description": "Load the purchase skill or its denial reference when needed for a purchase task.",
    "parameters": {"type": "object", "properties": {"resource": {"type": "string", "enum": [
        "propose-purchase", "propose-purchase/denials"]}},
        "required": ["resource"], "additionalProperties": False},
}
TERMINAL_DENIALS = {"proposal_limit", "plan_required", "plan_not_ready", "policy_changed",
                   "forbidden", "unauthorized", "internal_error"}


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def valid_arguments(name, args):
    """Small validator for the four advertised tools; never coerce model values."""
    if not isinstance(args, dict):
        return False
    if name == "get_catalog":
        return not args
    if name == "get_skill":
        return set(args) == {"resource"} and args["resource"] in (
            "propose-purchase", "propose-purchase/denials")
    if name == "get_purchase":
        return (set(args) == {"purchase_id"} and isinstance(args["purchase_id"], str)
                and 1 <= len(args["purchase_id"]) <= 128
                and all(c in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
                        for c in args["purchase_id"]))
    if name != "propose_purchase" or set(args) != {"items"}:
        return False
    items = args["items"]
    return (isinstance(items, list) and 1 <= len(items) <= 10
            and all(isinstance(i, dict) and set(i) == {"sku", "quantity"}
                    and isinstance(i["sku"], str) and 1 <= len(i["sku"]) <= 128
                    and type(i["quantity"]) is int and 1 <= i["quantity"] <= 100 for i in items))


class ShoppingAgent:
    def __init__(self, provider, runner, prompt, tool_specs):
        if {tool["name"] for tool in tool_specs} != {"get_catalog", "propose_purchase", "get_purchase"}:
            raise ValueError("Only the three scoped purchase tools may be registered.")
        self.provider = provider
        self.runner = runner
        self.system = prompt.strip() + "\n\n" + SKILL_DESCRIPTION
        self.tools = [*tool_specs, SKILL_TOOL]

    def run(self, task, *, progress=None):
        if not isinstance(task, str) or not task.strip() or len(task) > 4000:
            raise ValueError("Provide a shopping request of at most 4,000 characters.")
        start = time.monotonic()
        report = {"kind": "real_model_shopping_run", "run_id": str(uuid.uuid4()),
                  "started_at_utc": datetime.now(timezone.utc).isoformat(),
                  "provider": self.provider.provider, "model": self.provider.model,
                  "agent": self.runner.principal.identity, "request": task,
                  "prompt_sha256": digest(self.system),
                  "tools_sha256": digest(json.dumps(self.tools, sort_keys=True)),
                  "skill_sha256": {name: digest(text) for name, text in self.runner._skills.items()},
                  "generation": {"temperature": 0, "max_output_tokens": self.provider.max_output_tokens,
                                 "request_timeout_seconds": self.provider.timeout_seconds},
                  "bounds": {"model_calls": 9, "tool_calls": 8, "revised_proposals": 1},
                  "model_calls": 0, "tool_calls": 0, "proposals": 0,
                  "events": [], "usage": {}, "outcome": "no_purchase", "stop_reason": None,
                  "last_proposal": None, "model_message": "", "live_paypal": False,
                  "cost_usd": None,
                  "cost_note": "Token usage recorded; account tier and actual provider billing not inferred.",
                  "limitations": ["Synthetic catalog; no owner approval or payment tools.",
                                  "Model prose is not proof of a reservation or payment.",
                                  "Host retry keys survive response loss in this process, not a host restart."]}
        contents = [{"role": "user", "parts": [{"text": task}]}]
        finish_only = False
        known_tools = {t["name"] for t in self.tools}
        for _ in range(9):
            report["model_calls"] += 1
            if progress:
                progress({"phase": "request", "call": report["model_calls"]})
            request_start = time.monotonic()
            try:
                turn = self.provider.generate(contents, self.system, self.tools, tools_enabled=not finish_only)
            except ModelUnavailable as error:
                report["provider_error"] = {"code": error.code, "http_status": error.http_status}
                report["events"].append({"type": "model_error", "call": report["model_calls"],
                                         "elapsed_seconds": round(time.monotonic() - request_start, 3),
                                         "code": error.code, "http_status": error.http_status})
                if progress:
                    progress({"phase": "error", "call": report["model_calls"], "code": error.code})
                report["stop_reason"] = report["stop_reason"] or error.code
                break
            for key, amount in turn.usage.items():
                report["usage"][key] = report["usage"].get(key, 0) + amount
            report["events"].append({"type": "model", "call": report["model_calls"],
                                     "model_version": turn.model_version,
                                     "text": turn.text, "usage": turn.usage,
                                     "elapsed_seconds": round(time.monotonic() - request_start, 3)})
            if progress:
                progress({"phase": "response", "call": report["model_calls"], "tools": len(turn.calls)})
            # Protocol content retains opaque signatures in memory only. The
            # normalized report above excludes hidden thoughts and signatures.
            contents.append(turn.content)
            if turn.text:
                report["model_message"] = turn.text
            if not turn.calls:
                report["stop_reason"] = report["stop_reason"] or "model_returned_text"
                break
            if finish_only:
                report["stop_reason"] = report["stop_reason"] or "unexpected_final_tool_call"
                break
            if len(turn.calls) > 8 - self.runner.tool_calls:
                report["stop_reason"] = "tool_limit"
                break  # Reject the whole over-limit batch before executing it.
            responses = []
            for call in turn.calls:
                name, args = call["name"], call["args"]
                valid = name in known_tools and valid_arguments(name, args)
                if finish_only:
                    result = {"decision": "denied", "reason": "run_stopped"}
                else:
                    try:
                        # Invalid calls still consume the trusted dispatcher's
                        # call allowance, but cannot reach the gateway.
                        result = self.runner.call(name if valid else "__invalid__", args if valid else {})
                    except Rejection as error:
                        result = {"decision": "denied", "reason": error.code}
                report["events"].append({"type": "tool", "name": name if name in known_tools else "unavailable_tool",
                                         "arguments": args if valid else {"omitted": "invalid_arguments"},
                                         "result": result})
                if name == "propose_purchase" and valid and not finish_only:
                    report["last_proposal"] = result
                    if result.get("decision") == "pending":
                        report["outcome"] = "pending"
                    elif result.get("decision") == "reserved":
                        report["outcome"] = "reserved_for_owner"
                    else:
                        report["outcome"] = "denied"
                response = {"name": name, "response": result}
                if "id" in call:
                    response["id"] = call["id"]
                responses.append({"functionResponse": response})
                reason = self.runner.stop_reason
                if result.get("reason") in TERMINAL_DENIALS:
                    reason = result["reason"]
                if reason:
                    report["stop_reason"] = reason
                    finish_only = True
            contents.append({"role": "user", "parts": responses})
            # After a terminal result, allow one tools-disabled explanation. A
            # model can never reopen the dispatcher by saying more work is needed.
        else:
            report["stop_reason"] = report["stop_reason"] or "model_call_limit"
        report["tool_calls"] = self.runner.tool_calls
        report["proposals"] = self.runner.proposals
        report["elapsed_seconds"] = round(time.monotonic() - start, 3)
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        return report
