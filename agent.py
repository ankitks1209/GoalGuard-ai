"""Source-checkout CLI for real Gemini callers using only scoped purchase tools."""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import uuid

from goalguard.gateway import Principal
from goalguard.http_tools import ScopedHTTPGateway
from goalguard.models import Gemini, ModelUnavailable, model_config
from goalguard.runner import ProposalRunner
from goalguard.shopping import ShoppingAgent


def provenance(root):
    revision, dirty = None, None
    try:
        revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root,
                                           stderr=subprocess.DEVNULL, text=True).strip()
        dirty = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=root,
                                             stderr=subprocess.DEVNULL, text=True).strip())
    except (OSError, subprocess.CalledProcessError):
        pass
    return {"source_revision": revision, "source_tree_dirty": dirty,
            "python": platform.python_version(), "command": "python agent.py (private arguments omitted)"}


def private_record(path, report, root):
    resolved = path.resolve()
    if resolved.is_relative_to(root) and not resolved.is_relative_to(root / ".local"):
        raise ValueError("Keep private transcripts in .local/ or outside the repository.")
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w") as file:
        json.dump(report, file, indent=2, allow_nan=False)
        file.write("\n")


def show_progress(identity, event):
    if event["phase"] == "request":
        message = f"Gemini request {event['call']}/9…"
    elif event["phase"] == "response":
        message = f"Request {event['call']} returned ({event['tools']} tool calls)."
    else:
        message = f"Request {event['call']} stopped: {event['code']}."
    try:
        print(f"  [{identity}] {message}", file=sys.stderr, flush=True)
    except OSError:
        pass  # A failed console write cannot alter proposal authority/state.


def make_caller(root, config, identity, token, port, *, timeout=60):
    model = config["GEMINI_MODEL_A" if identity == "agent-a" else "GEMINI_MODEL_B"]
    provider = Gemini(config["GEMINI_API_KEY"], model, timeout=timeout)
    gateway = ScopedHTTPGateway(identity, token, port=port)
    skills = {"propose-purchase": (root / "skills/propose-purchase/SKILL.md").read_text(),
              "propose-purchase/denials": (root / "skills/propose-purchase/references/denials.md").read_text()}
    runner = ProposalRunner(gateway, Principal("demo-home", identity, "agent"), skills=skills)
    prompt = (root / "prompts/shopping-agent.txt").read_text()
    tools = json.loads((root / "agent-tools.json").read_text())["tools"]
    return ShoppingAgent(provider, runner, prompt, tools)


def run_demo(root, config, *, timeout=60, only_agent=None):
    """Fresh synthetic household, real models and local HTTP; no payment adapter."""
    from http.server import ThreadingHTTPServer
    import secrets
    import threading

    from demo import sample_plan
    from goalguard import Ledger
    from goalguard.catalog import Catalog
    from goalguard.gateway import Gateway
    from server import make_handler

    # Fail on missing configuration before any setup or external generation.
    identities = [only_agent] if only_agent else ["agent-a", "agent-b"]
    for identity in identities:
        key = "GEMINI_MODEL_A" if identity == "agent-a" else "GEMINI_MODEL_B"
        Gemini(config["GEMINI_API_KEY"], config[key], timeout=timeout)
    directory = root / ".local/agent-demos" / str(uuid.uuid4())
    session_path = directory / "session.json"
    session = {"kind": "single_live_agent_demo" if only_agent else "sequential_live_agent_demo", "status": "started",
               "started_at_utc": datetime.now(timezone.utc).isoformat(),
               "provenance": provenance(root), "agents": [], "requested_agents": identities,
               "paypal": "not_configured",
               "scope": "Real Gemini calls, synthetic catalog/plan, fresh disposable SQLite, actual scoped loopback HTTP.",
               "limitations": ["Sequential demonstration, not a concurrency evaluation or baseline comparison.",
                               "Setup script acts as owner only to confirm the synthetic financial plan.",
                               "No purchase approvals or payments. Demo reservations disappear at exit.",
                               "A completed demo does not prove the remaining real-agent milestone."]}
    private_record(session_path, session, root)
    print("REAL MODEL DEMO — synthetic household/products; no PayPal connection or payments.", flush=True)
    print("Synthetic discretionary capacity: $350. Existing state is untouched.", flush=True)
    print(f"Requested agents: {', '.join(identities)}. This is not a concurrency evaluation.", flush=True)
    print(f"Private records: {directory}", flush=True)
    try:
        with tempfile.TemporaryDirectory(prefix="goalguard-live-demo-") as state:
            ledger = Ledger(Path(state) / "ledger.sqlite")
            ledger.create_household("demo-home", 0, 0)
            gateway = Gateway(ledger, Catalog(), paypal=None, require_plan=True)
            owner = Principal("demo-home", "owner", "owner")
            spec = sample_plan()
            preview = gateway.plan(owner, "preview", {"plan": spec, "mode": "activate"})
            gateway.plan(owner, "confirm", {"plan": spec, "mode": "activate", "preview_hash": preview["preview_hash"]})
            tokens = {role: secrets.token_urlsafe(32) for role in ("owner", "agent-a", "agent-b")}
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(gateway, tokens))
            server.daemon_threads = True
            worker = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.1), daemon=True)
            worker.start()
            try:
                requests = [
                    ("agent-a", "Find one USB microphone with headphone monitoring. I prefer the standard model; if the gateway cannot reserve it, a budget model with both required features is acceptable."),
                    ("agent-b", "Find one vacuum for floor cleaning. I prefer the standard model; if the gateway cannot reserve it, a compact model with floor-cleaning capability is acceptable."),
                ]
                for identity, task in requests:
                    if identity not in identities:
                        continue
                    print(f"Running {identity}…", flush=True)
                    caller = make_caller(root, config, identity, tokens[identity], server.server_port, timeout=timeout)
                    record = directory / f"{identity}.json"
                    private_record(record, {"status": "started", "agent": identity}, root)
                    report = caller.run(task, progress=lambda event: show_progress(identity, event))
                    report["provenance"] = session["provenance"]
                    with record.open("w") as file:
                        json.dump(report, file, indent=2, allow_nan=False)
                        file.write("\n")
                    results = [event["result"] for event in report["events"]
                               if event["type"] == "tool" and event["name"] == "propose_purchase"]
                    denied = any(result.get("reason") == "budget_exceeded" for result in results)
                    summary = {"agent": identity, "model": report["model"], "outcome": report["outcome"],
                               "stop_reason": report["stop_reason"], "model_calls": report["model_calls"],
                               "tool_calls": report["tool_calls"], "budget_denial_observed": denied,
                               "recovered_after_denial": denied and report["outcome"] == "reserved_for_owner",
                               "last_proposal": report["last_proposal"], "provider_error": report.get("provider_error"),
                               "private_record": str(record)}
                    session["agents"].append(summary)
                    print(json.dumps(summary, indent=2), flush=True)
                    if report.get("provider_error"):
                        break  # No retry storm or silent provider/model fallback.
                accounting = ledger.summary("demo-home")
                session["final_demo_accounting"] = {key: accounting[key] for key in (
                    "available_cents", "encumbered_cents", "spent_cents")}
                session["status"] = "completed" if (len(session["agents"]) == len(identities) and all(
                    item["outcome"] == "reserved_for_owner" and not item["provider_error"]
                    for item in session["agents"])) else "needs_review"
            finally:
                server.shutdown()
                server.server_close()
                worker.join(timeout=3)
    except BaseException:
        session["status"] = "interrupted_or_setup_failed"
        raise
    finally:
        session["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        with session_path.open("w") as file:
            json.dump(session, file, indent=2, allow_nan=False)
            file.write("\n")
    print(json.dumps({"status": session["status"], "agents_run": len(session["agents"]),
                      "requested_agents": identities,
                      "denial_recovery_observed": any(a["recovered_after_denial"] for a in session["agents"]),
                      "final_demo_accounting": session.get("final_demo_accounting"),
                      "payments": "none", "demo_state": "discarded", "private_session": str(session_path)}, indent=2))
    if session["status"] != "completed":
        raise SystemExit(1)


def main():
    root = Path(__file__).resolve().parent
    default_state = Path(tempfile.gettempdir()) / (
        "goalguard-runtime-" + hashlib.sha256(str(root).encode()).hexdigest()[:12])
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--agent", choices=("agent-a", "agent-b"), default="agent-a")
    parser.add_argument("--request", help="Shopping need; do not include private financial details.")
    parser.add_argument("--state-dir", type=Path, default=default_state,
                        help="Same state directory as server.py; only its agent token is used.")
    parser.add_argument("--env-file", type=Path, default=root / ".env.models")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--timeout", type=int, default=60, help="Model network timeout in seconds (10–120; default 60).")
    parser.add_argument("--record", type=Path, help="New private transcript path; never overwrite an existing run.")
    diagnostics = parser.add_mutually_exclusive_group()
    diagnostics.add_argument("--check-config", action="store_true", help="Show presence only; no model/API requests.")
    diagnostics.add_argument("--list-models", action="store_true",
                             help="Check Gemini model metadata without a shopping task or gateway tokens.")
    diagnostics.add_argument("--demo", action="store_true",
                             help="Run two real models against a fresh synthetic household; no PayPal payments.")
    parser.add_argument("--only-agent", choices=("agent-a", "agent-b"),
                        help="With --demo, isolate one model/caller. Completion applies only to that caller.")
    args = parser.parse_args()
    if args.only_agent and not args.demo:
        parser.error("--only-agent requires --demo.")
    try:
        config = model_config(args.env_file)
        model = config["GEMINI_MODEL_A" if args.agent == "agent-a" else "GEMINI_MODEL_B"]
        if args.demo:
            run_demo(root, config, timeout=args.timeout, only_agent=args.only_agent)
            return
        if args.check_config:
            print(json.dumps({"provider": "gemini", "api_key_present": bool(config["GEMINI_API_KEY"]),
                              "agent": args.agent, "model": model or None,
                              "server_token_file_present": (args.state_dir / "tokens.json").is_file(),
                              "live_call": "not_run"}, indent=2))
            return
        if args.list_models:
            listing = Gemini(config["GEMINI_API_KEY"], model or "model-list", timeout=args.timeout).list_models()
            print(json.dumps({"status": "succeeded", "operation": "model_list",
                              "configured_models_listed": {config[key]: config[key] in listing["models"]
                                  for key in ("GEMINI_MODEL_A", "GEMINI_MODEL_B") if config[key]},
                              "available_generation_models": listing["models"],
                              "list_complete": listing["list_complete"],
                              "generation": "not_run", "gateway": "not_contacted",
                              "note": "Model listing does not prove generation quota, free-tier eligibility or a working agent."}, indent=2))
            return
        if not args.request or not args.request.strip() or len(args.request) > 4000:
            parser.error("Provide --request with a shopping need of at most 4,000 characters.")
        Gemini(config["GEMINI_API_KEY"], model, timeout=args.timeout)
        token_values = json.loads((args.state_dir / "tokens.json").read_text())
        if (not isinstance(token_values, dict) or set(token_values) != {"owner", "agent-a", "agent-b"}
                or any(not isinstance(v, str) or len(v) < 32 for v in token_values.values())
                or len(set(token_values.values())) != 3):
            raise ValueError("Invalid scoped token file; its values were not logged.")
        token = token_values[args.agent]
        del token_values  # No owner credential is passed to the caller or model.
        caller = make_caller(root, config, args.agent, token, args.port, timeout=args.timeout)
        # Validate and reserve the record path before model usage/reservations.
        record = args.record or root / ".local/agent-runs" / (str(uuid.uuid4()) + ".json")
        private_record(record, {"status": "started", "agent": args.agent}, root)
        report = caller.run(args.request, progress=lambda event: show_progress(args.agent, event))
        report["provenance"] = provenance(root)
        # The exclusive creation above set this private file's mode to 0600.
        with record.open("w") as file:
            json.dump(report, file, indent=2, allow_nan=False)
            file.write("\n")
        print(json.dumps({"outcome": report["outcome"], "stop_reason": report["stop_reason"],
                          "last_proposal": report["last_proposal"],
                          "model_message_untrusted": report["model_message"],
                          "model_calls": report["model_calls"], "tool_calls": report["tool_calls"],
                          "provider_error": report.get("provider_error"),
                          "private_record": str(record)}, indent=2))
        if report.get("provider_error"):
            raise SystemExit(1)
    except ModelUnavailable as error:
        print(json.dumps({"status": "failed", "code": error.code, "http_status": error.http_status,
                          "generation": "not_run", "gateway": "not_contacted"}, indent=2))
        raise SystemExit(1)
    except FileNotFoundError:
        parser.exit(2, "Required configuration, server tokens or source assets are missing. Start from docs/agents.md.\n")
    except FileExistsError:
        parser.exit(2, "Record already exists; use a new path. No existing transcript was overwritten.\n")
    except (ValueError, KeyError, TypeError, OSError):
        parser.exit(2, "Agent setup/run failed. Check docs/agents.md and local configuration; secret values were not logged.\n")


if __name__ == "__main__":
    main()
