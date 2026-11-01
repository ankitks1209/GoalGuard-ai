# GoalGuard API walkthrough with Postman

This collection tests the existing API against an isolated synthetic household.
It makes no Gemini, PayPal or retailer request. It demonstrates deterministic
API behavior, not an AI-agent or payment-provider run.

## Run

From the repository root, start a fresh fixture with a new ignored output path:

```sh
.venv/bin/python scripts/postman_fixture.py --environment .local/checks/postman-fixture.json
```

Leave it running. In a second terminal, use the official Postman CLI:

```sh
postman collection run postman/goalguard.postman_collection.json \
  --environment .local/checks/postman-fixture.json \
  --no-report-events --bail
```

CLI setup is described in the
[official installation guide](https://learning.postman.com/docs/postman-cli/postman-cli-installation/).
The collection uses the portable v2.1 format. It may also be imported with the
generated environment into Postman for local use; that app workflow has not
been verified. Do not sync the generated environment or run evidence to a
shared workspace. The example environment has blank values and cannot run.

Run the collection once per fresh fixture. Stop with Ctrl-C when finished;
its temporary ledger is discarded. A second run against the same fixture
intentionally fails the initial unconfirmed-plan check. Choose a new environment
filename for the next fixture; existing files are never overwritten.

The fixture has its own ephemeral loopback port and random synthetic tokens.
It never reads `.env`, `.env.models`, existing tokens or a household database.
The generated environment has mode 0600 and must remain private under `.local/`.

## What it checks

Eighteen requests cover authentication, agent access restrictions, plan preview
without activation, exact-plan confirmation, synthetic catalog labels, shared
reservations, identical retry identity, changed-key payload rejection, budget
denial and a returned alternative, exact-cart owner consent, and an audit event.
The final accounting checks distinguish committed capacity from captured spend.

Confirmation and consent in this collection are automated fixture assertions.
They never represent a real person's consent. Only the disposable fixture may
be used; do not repoint it at an existing household. No checkout, authorization,
capture, void or model-drafting requests are included.

The collection has a loopback/fixture guard and disables redirects. Those are
operator checks, not a replacement for the server's authority enforcement.
It uses bearer clients; browser cookie/CSRF/session behavior remains covered by
the separate Python/browser suites.

## Tool installation and verification status

Verified 27 October 2026 with official Postman CLI **1.80.0**: **18 requests,
45 assertions, zero failures**, one iteration, exit 0. See the
[sanitized run summary](../reports/postman-demo.json). This was an actual local
Postman execution against the fixture, with event reporting disabled and no
Postman login. The CLI noted that publishing run details needs credentials;
no publication was requested. This is not hosted/CI or provider evidence.

For this host, the official macOS ARM64 CLI archive from `dl-cli.pstmn.io` was
extracted only below ignored `.local/tools/postman/`. Invoke it here as
`.local/tools/postman/postman-cli` in place of `postman` in the command above.
Archive integrity passed. Apple signature verification with the Postman team
requirement passed outside the sandbox after failing inside it. A help invocation
occurred prematurely before that failure was resolved; the collection itself
ran only after successful verification. No npm/Python dependency, shell profile,
global agent instruction or Postman workspace was modified. The downloaded
installer was inspected but will not be executed: it also edits global agent
instructions and adds a user-level symlink.

APIMatic remains a separate candidate: its documented ContextMatic endpoint
returned HTTP 401 requiring OAuth on this host. No successful context lookup
or integration is claimed. See
[competition readiness](../agent_docs/competition-readiness.md).
