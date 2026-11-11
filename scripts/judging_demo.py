"""Launch a disposable browser walkthrough with no model or payment providers."""

import argparse
from http.server import ThreadingHTTPServer
from pathlib import Path
from tempfile import TemporaryDirectory

from demo import sample_plan
from goalguard import Ledger
from goalguard.catalog import Catalog
from goalguard.gateway import Gateway, Principal
from server import make_handler, token_config

ROOT = Path(__file__).resolve().parents[1]


def make_workspace(directory: Path) -> Gateway:
    ledger = Ledger(directory / "ledger.sqlite")
    ledger.create_household("demo-home", 0, 0)
    gateway = Gateway(ledger, Catalog(), require_plan=True)
    owner = Principal("demo-home", "owner", "owner")
    spec = sample_plan()
    preview = gateway.plan(owner, "preview", {"plan": spec, "mode": "activate"})
    gateway.plan(owner, "confirm", {"plan": spec, "mode": "activate",
                                   "preview_hash": preview["preview_hash"]})

    def propose(agent: str, key: str, sku: str):
        return gateway.propose(Principal("demo-home", agent, "agent"), {
            "request_key": key, "items": [{"sku": sku, "quantity": 1}],
        })

    mic = propose("agent-a", "judge-microphone", "mic-standard")
    vacuum = propose("agent-b", "judge-vacuum", "vacuum-standard")
    if mic["decision"] != "reserved" or vacuum.get("reason") != "budget_exceeded":
        raise RuntimeError("The synthetic budget scenario no longer matches the walkthrough.")
    alternative = vacuum["counteroffers"][0]["cart"]["items"][0]
    recovered = propose("agent-b", "judge-vacuum-alternative", alternative["sku"])
    if recovered["decision"] != "reserved":
        raise RuntimeError("The synthetic budget alternative could not be reserved.")
    return gateway


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=0, help="Loopback port (default: choose a free port).")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("Use a port from 0 to 65535.")
    assets = ROOT / "frontend" / "dist"
    if not (assets / "index.html").is_file():
        parser.error("Built interface missing. Build frontend or extract the complete judging bundle.")
    with TemporaryDirectory(prefix="goalguard-judging-") as directory:
        state = Path(directory)
        gateway = make_workspace(state)
        key_file = state / "tokens.json"
        try:
            http = ThreadingHTTPServer(("127.0.0.1", args.port),
                                       make_handler(gateway, token_config(key_file), static_root=assets))
        except OSError:
            parser.exit(1, "Could not bind localhost. Use the default port or an unused port.\n")
        with http:
            print("Synthetic walkthrough: no Gemini or PayPal calls.\n"
                  f"Workspace: http://127.0.0.1:{http.server_port}/\n"
                  f"Private owner key file: {key_file}\n"
                  "Use the owner entry. Reservations last 15 minutes. Stop with Ctrl-C.", flush=True)
            try:
                http.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()
