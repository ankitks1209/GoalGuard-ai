"""Disposable Postman API fixture: synthetic finances, no model/payment providers."""

import argparse
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import secrets
import sys
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from demo import sample_plan
from goalguard import Ledger
from goalguard.catalog import Catalog
from goalguard.gateway import Gateway
from server import make_handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--environment", type=Path, required=True,
                        help="New private Postman environment JSON path; never overwritten.")
    args = parser.parse_args()
    destination = args.environment.resolve()
    if destination.exists():
        parser.error("Environment already exists; choose a new private output path.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    tokens = {role: secrets.token_urlsafe(32) for role in ("owner", "agent-a", "agent-b")}
    with tempfile.TemporaryDirectory(prefix="goalguard-postman-") as directory:
        ledger = Ledger(Path(directory) / "ledger.sqlite")
        ledger.create_household("demo-home", 0, 0)
        gateway = Gateway(ledger, Catalog(), require_plan=True)
        with ThreadingHTTPServer(("127.0.0.1", 0), make_handler(gateway, tokens)) as http:
            values = {
                "base_url": f"http://127.0.0.1:{http.server_port}",
                "fixture_mode": "disposable-no-providers",
                "owner_token": tokens["owner"],
                "agent_a_token": tokens["agent-a"],
                "agent_b_token": tokens["agent-b"],
                "demo_plan": json.dumps(sample_plan(), separators=(",", ":")),
            }
            environment = {
                "name": "GoalGuard disposable synthetic fixture",
                "_postman_variable_scope": "environment",
                "values": [{"key": key, "value": value, "enabled": True,
                            "type": "secret" if key.endswith("_token") else "default"}
                           for key, value in values.items()],
            }
            descriptor = os.open(destination, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "w") as output:
                json.dump(environment, output, indent=2)
                output.write("\n")
            print("Synthetic Postman fixture ready; environment saved privately.", flush=True)
            print("No model or payment provider is configured. Stop with Ctrl-C.", flush=True)
            try:
                http.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()
