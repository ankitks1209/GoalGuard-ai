"""Source-checkout demonstration of owner text -> unconfirmed initial plan."""

import argparse
from datetime import datetime, timezone
from http.server import ThreadingHTTPServer
import json
from pathlib import Path
import secrets
import tempfile
import threading
from urllib.error import HTTPError, URLError
from urllib.request import ProxyHandler, Request, build_opener
import uuid

from agent import private_record, provenance
from demo import sample_plan
from goalguard import Ledger
from goalguard.catalog import Catalog
from goalguard.drafting import PlanDrafter
from goalguard.gateway import Gateway
from goalguard.http_tools import NoRedirect
from goalguard.models import Gemini, model_config
from server import make_handler


def synthetic_request():
    spec = sample_plan()
    return ("My spending cash is $600, excluding separately held savings. Keep a $50 buffer. "
            f"My only unpaid bill is Utilities for $100 due {spec['bills'][0]['due_date']}. "
            f"My next expected income is $400 on {spec['next_income']['due_date']}. "
            "My goal is Studio fund: total target $600, already saved separately $300, "
            f"deadline {spec['goal']['target_date']}. Please suggest the monthly contribution.")


def main():
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--demo", action="store_true", required=True,
                        help="Send the built-in synthetic request to Gemini; never confirm a plan.")
    parser.add_argument("--env-file", type=Path, default=root / ".env.models")
    parser.add_argument("--timeout", type=int, default=60)
    args = parser.parse_args()
    config = model_config(args.env_file)
    provider = Gemini(config["GEMINI_API_KEY"], config["GEMINI_MODEL_B"], timeout=args.timeout)
    drafter = PlanDrafter(provider)
    request_text = synthetic_request()
    record = root / ".local/plan-drafts" / (str(uuid.uuid4()) + ".json")
    report = {"kind": "owner_plan_draft_demo", "status": "started",
              "started_at_utc": datetime.now(timezone.utc).isoformat(),
              "request": request_text, "input": "built-in synthetic financial request",
              "provenance": provenance(root), "model": provider.model,
              "paypal": "not_configured", "confirmation": "not_requested"}
    private_record(record, report, root)
    print("OWNER DRAFT DEMO — synthetic inputs; one real model extraction; no activation or payments.", flush=True)
    print(f"Private record: {record}", flush=True)
    try:
        with tempfile.TemporaryDirectory(prefix="goalguard-plan-draft-") as directory:
            ledger = Ledger(Path(directory) / "ledger.sqlite")
            ledger.create_household("demo-home", 0, 0)
            gateway = Gateway(ledger, Catalog(), paypal=None, require_plan=True, drafter=drafter)
            tokens = {role: secrets.token_urlsafe(32) for role in ("owner", "agent-a", "agent-b")}
            server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(gateway, tokens))
            server.daemon_threads = True
            worker = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.1), daemon=True)
            worker.start()
            opener = build_opener(ProxyHandler({}), NoRedirect())
            base = f"http://127.0.0.1:{server.server_port}"
            def owner_request(path, body=None):
                req = Request(base + path, data=json.dumps(body).encode() if body is not None else None,
                              headers={"Authorization": "Bearer " + tokens["owner"], "Content-Type": "application/json"})
                try:
                    res = opener.open(req, timeout=args.timeout + 10)
                except HTTPError as error:
                    res = error
                with res:
                    return res.code, json.load(res)
            try:
                print("Extracting plan inputs…", flush=True)
                status, result = owner_request("/v1/plan/draft", {
                    "request": request_text, "timezone": "UTC", "currency": "USD",
                    "allow_model_processing": True})
                _, snapshot = owner_request("/v1/plan")
                report.update(http_status=status, result=result,
                              active_plan_created=snapshot.get("plan") is not None,
                              draft_saved=snapshot.get("draft") is not None,
                              status=result.get("status", "failed"))
            finally:
                server.shutdown()
                server.server_close()
                worker.join(timeout=3)
    except (OSError, URLError, ValueError):
        report["status"] = "local_transport_or_output_error"
    finally:
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        with record.open("w") as file:
            json.dump(report, file, indent=2, allow_nan=False)
            file.write("\n")
    result = report.get("result", {})
    calculation = result.get("calculation", {})
    print(json.dumps({"status": report["status"], "http_status": report.get("http_status"),
                      "plan": result.get("plan"), "questions": result.get("questions"),
                      "issues": result.get("issues"), "reason": result.get("reason"),
                      "computed_fields": result.get("computed_fields"),
                      "available_cents": calculation.get("available_cents"),
                      "suggested_contribution_cents": (calculation.get("goal") or {}).get("suggested_contribution_cents"),
                      "active_plan_created": report.get("active_plan_created"),
                      "draft_saved": report.get("draft_saved"), "confirmation": "not_requested",
                      "payments": "none", "private_record": str(record)}, indent=2))
    if report["status"] != "draft_ready" or report.get("active_plan_created"):
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError):
        raise SystemExit("Draft setup failed. Check local model configuration; secret values were not logged.") from None
