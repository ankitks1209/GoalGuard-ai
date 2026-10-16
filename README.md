# GoalGuard

**A budget firewall for AI shopping agents.**

This is the first implementation stage: a deterministic ledger, consent engine,
scoped tool API, PayPal sandbox adapter, and local evaluation harness. It is not
yet a completed PayPal + AI hackathon submission: real LLM callers,
a buyer-facing interface, and user validation are outstanding. The financial-plan
backend is implemented and locally checked. The core
payment lifecycle has now been verified against actual PayPal sandbox.

## Run the local checks

Use Python 3.11 or later. There are no third-party dependencies.

```sh
python3 evaluate.py --report eval-report.json
python3 demo.py
```

Run these commands from this directory. `demo.py` uses a temporary database and
prints a failure-first comparison, a denial, a feasible counteroffer, and an owner
approval audit. The products and tool callers are simulated. It makes no PayPal
or LLM requests. Either concurrent request can win; the invariant is independent
of their execution order.

The recorded evaluation contains **155 cases: 155 passed, 0 skipped, 0 failures,
0 errors**. Eight checks use actual loopback TCP, including all five originally
skipped TCP cases, two privacy checks and the financial-plan route check. Seven in-memory checks independently
exercise the HTTP handler. The report lists the TCP cases explicitly.
Payment-adapter checks use handwritten fixtures and four offline regression cases
replaying sanitized actual sandbox responses. Three process-kill checks
terminate a test-owned worker after a simulated provider action but before its
ledger completion, then reconcile without another payment request. These prove
local crash recovery against fixtures, not real PayPal settlement.
See `eval-report.json` for the machine-readable result.

## Actual sandbox evidence

Gate 2 core lifecycle passed on 17 October 2026 (Asia/Kolkata). Genuine manual
buyer approval was verified through PayPal's order API before authorization.
One $1.00 USD order was authorized and captured. A same-key provider replay
returned the same capture ID; a gateway retry made no additional provider calls.
A second $1.00 authorization was voided and verified by GET, restoring its budget.
No known authorization hold remains from these scenarios. No fallback was used.

Deliberately suppressing the second successful authorization reply left capacity
reserved until real provider refresh recovered its status. This was a controlled
local fault, not a natural timeout or process kill. The local ledger guard also
rejected a 101-cent cart against the actual 100-cent approved authorization with
zero provider calls during that guard check; an earlier GET is excluded.

Observed responses: authorization returned an Order marked `COMPLETED` containing
a `CREATED` authorization and no capture; initial capture returned HTTP 201 and
same-key replay HTTP 200; void returned HTTP 200 with a `VOIDED` body. Payment
resource state, not Order completion alone, determines captured spending.

See [the sandbox report](docs/SANDBOX_VERIFICATION.md),
[machine-readable outcomes](docs/sandbox-results.json), and 29 sanitized responses
under `tests/fixtures/paypal-sandbox/`. Local suite results remain separate from
actual provider observations. Honor periods, long-duration expiry and provider
overcapture allowances were not verified by this run.

## Ledger and expiry

All money is integer USD cents. The owner-confirmed calendar-month plan stores
bills, buffer and a savings goal separately. It protects bills through the later
of month end and the next expected payday, including bills due on that payday.
Future income affects a separate forecast and never funds purchases before receipt.
Missing/overdue income information and month end freeze new purchases. After a
receipt is fully recorded, the owner confirms the next expected payday to extend
the horizon. Inputs and external payments remain self-reported, without bank sync.

```text
cash_base = opening cash + confirmed inflows - recorded external outflows
protected = unpaid protected bills + buffer + unfulfilled savings contribution
available = cash_base - protected - captured spending - encumbered purchases
new reservations require available >= 0
```

Each purchase contributes exactly once. Captured spending remains deducted;
capture moves the purchase from encumbered to spent. Releasing a captured purchase
would be an accounting error. Actual cash corrections may reveal a deficit;
display it and block new purchases while retaining payment obligations. Received
refunds are deduplicated cash credits, not capture reversals. Rollover rebases old
spend into new opening cash and carries verified authorizations exactly once.

An external bill payment pairs its cash debit with reduced bill protection in one
transaction. A savings deposit pairs the debit, fulfilled installment and increased
saved balance; earmarking alone is not a deposit. Financial edits invalidate
pre-payment approvals but retain authorized purchases' original settlement terms.
Title-only and expected-income-amount-only edits preserve approvals. In-flight or
uncertain payments block financial edits; actual cash events can still be recorded.

The 43 new financial checks cover period boundaries, goal arithmetic, paired cash
events, deficits, privacy, revision/authorization races, rollover and migration
safety. See [the implemented financial API](docs/FINANCIAL_PLAN_API.md).
Legacy aggregate-only APIs remain for existing tests; the running server requires
an explicit owner-confirmed financial plan. No plan is activated automatically.

```text
reserved -> approved -> authorizing -> authorized -> capturing -> captured
    |           |                        |
    +-> released/expired                 +-> voiding -> voided

authorizing/capturing/voiding -> reconcile_pending -> verified payment outcome
```

Proposals are validated before entering the ledger. Denied proposals allocate
nothing. `BEGIN IMMEDIATE` serializes all SQLite writers, including different
households. This is a deliberately conservative prototype; a larger deployment
would use per-household transaction locking in a database such as PostgreSQL.

Reservations have a **15-minute TTL**. It is measured from the original reserve
and is not extended by approval or retries. At `server_now >= expires_at`, owner
approval and initiation of authorization are denied. That decision happens while
holding the database write transaction. Approval just before expiry does not
guarantee a later authorization will start in time.

Reserved and approved purchases expire on access or in the server's five-second
sweep. Once payment I/O starts, local TTL cannot release money: the payment may
have succeeded even if its response was lost. Authorizing, authorized, capturing,
voiding, and unresolved purchases remain counted until their outcome is verified.

## Trust boundary

- Agents can inspect the synthetic catalog, propose SKU/quantity pairs, and inspect
  a redacted own-purchase status. Owner audit and full financial records are private.
- Agent responses use allowlists, including errors, denials and counteroffers.
  They exclude bills, buffer, savings goals, internal financial totals and payment
  credentials. The legacy budget route returns only a conservative $50 headroom
  floor for agents; it is absent from the default model tool set.
- `ProposalRunner` enforces eight tool calls and one revised proposal. It generates
  request keys, retains the key after a simulated lost response, and stops after
  a reservation or exhausted revisions. It is a dispatcher, not a live model runner.
- The gateway persists a limit of three distinct proposals per agent and trusted
  planning period, counting denied proposals too. Same-key/same-cart retries reuse
  a slot; changing a cart under that key is rejected. Confirmed plans supply the
  period ID, including a check against rollover between quota and reservation.
  Legacy aggregate-only test scenarios retain a fixed prototype ID.
- Counteroffers expose at most one inexpensive feasible catalog alternative, not
  exact remaining capacity. Decision outcomes and the optional headroom floor still
  leak information. Caps are not a privacy guarantee and may block legitimate work.
- Agents cannot submit prices, consent, household IDs, or payment credentials.
- Owner endpoints grant consent and execute payment actions. Do not provide owner
  credentials or consent permits to an LLM.
- The server recomputes prices from the catalog. A malicious product description
  cannot alter the ledger, grants, or protected commitments.
- A signed consent permit binds household, proposing agent, cart hash, complete
  amount, currency, policy version, and authorization-initiation deadline.
- A server record binds the PayPal order. Before money actions, the adapter checks
  actual merchant, cart, quantities, delivered total, currency, and purchase ID.
- One durable operation ID controls each authorization, capture, or void and is
  sent to PayPal as `PayPal-Request-Id`. Retried completed operations return their
  recorded result; uncertain operations require status refresh.
- Initiation consent is explicitly consumed in the same write transaction as
  the authorization intent. The durable intent records action, cart, amount and
  provider IDs before the money-moving request is sent.

The permit's checkout deadline governs the start of authorization. Later capture
or void of a valid authorization is part of completing that approved payment
lifecycle; it does not use the original checkout TTL as a fulfilment deadline.

## Start the tool API

```sh
python3 server.py --port 8765
```

The server binds only to `127.0.0.1`. It stores runtime state in a private,
project-specific temporary directory outside the source repository, generates
three scoped tokens, and creates a bootstrap household requiring plan setup. Its signing
key is a separate file with mode `0600`, not a database setting. The server rejects
a `--state-dir` inside the source repository. For persistent demo state, supply an
external directory explicitly; temporary state can be cleaned by the operating
system. Never publish runtime files. The owner token is a prototype control,
not production user authentication.

Every request requires `Authorization: Bearer <scoped token>`.

| Endpoint | Scope | Body |
|---|---|---|
| `GET /v1/catalog` | Agent or owner | None |
| `GET /v1/budget` | Owner full view; agent coarse floor | None |
| `GET /v1/plan` | Owner | None |
| `POST /v1/plan/preview` | Owner | `plan`, `mode` |
| `POST /v1/plan/confirm` | Owner | `plan`, `mode`, `preview_hash` |
| `POST /v1/plan/cash-events` | Owner | `event_id`, `kind`, `amount_cents`, `reference_id` |
| `GET /v1/plan/audit` | Owner | None |
| `POST /v1/proposals` | Agent | `items`, `request_key` |
| `GET /v1/purchases/{id}` | Proposing agent or owner | None |
| `GET /v1/purchases/{id}/audit` | Owner | None |
| `POST /v1/purchases/{id}/approve` | Owner | `cart_hash` |
| `POST /v1/purchases/{id}/release` | Owner | `{}` |
| `POST /v1/purchases/{id}/checkout` | Owner | `{}` |
| `POST /v1/purchases/{id}/authorize` | Owner | `permit` |
| `POST /v1/purchases/{id}/capture` | Owner | `permit` |
| `POST /v1/purchases/{id}/void` | Owner | `permit` |
| `POST /v1/purchases/{id}/refresh` | Owner | `operation_id` |

Example proposal:

```json
{
  "items": [{"sku": "mic-standard", "quantity": 1}],
  "request_key": "recording-setup-001"
}
```

An insufficient-budget response contains `decision: denied`, a structured
`budget_exceeded` reason and at most one feasible counteroffer, without exact
headroom, private commitment names or financial totals.
Counteroffers are computed by enumerating the tiny catalog and retaining the
same declared functional requirements. Their suitability is synthetic, not a
claim about real microphone or vacuum products. A counteroffer needs a new request
key and a fresh budget check; it does not itself grant permission.

The interface is agent-neutral. Two scoped HTTP clients are represented in the
tests, but **two different real models/frameworks have not been demonstrated**.
`agent-tools.json` contains a provider-neutral tool schema for that next stage.
Model proposal arguments contain only items; trusted transport adds the HTTP
request key. Model tools omit the full budget and owner audit endpoints.

## Synthetic probing evidence

`python3 probe_evaluate.py --report probing-report.json` runs one deterministic
binary-search scenario for ten synthetic headrooms under two quota configurations
(20 runs, one run per capacity/configuration). The deliberately fine-grained test
catalog prices a unit at one cent and gives the attacker a known 0–100 cent domain.
Accepted reservations remain counted; there is no attacker-controlled reset.

In this finite experiment, the three-proposal cap had zero exact recoveries out
of ten and zero quota bypasses. The 32-proposal comparison recovered all ten exact
amounts. With a true 73-cent initial headroom, three evaluated proposals narrowed
it to 62–74 cents before the fourth was blocked. Capacity information still leaks;
this is not a live-model privacy evaluation or a general protection guarantee.
Multiple authorized agents may combine observations. See `probing-report.json`
for transcripts, candidate intervals and limitations.

## Configure the PayPal sandbox adapter

Fill the local `.env` using `.env.example`, or export those environment variables.
The server now reads `.env` without executing shell expressions. Environment
variables take precedence. Neither configuration values nor secrets are logged.
Use sandbox business credentials and that business's sandbox merchant ID. The
adapter has a fixed sandbox URL and cannot target live PayPal.
See [PAYPAL_SETUP.md](PAYPAL_SETUP.md) for where to get these credentials.

1. Preview and confirm a financial plan with the owner token using the documented
   plan API, then submit a proposal with an agent token.
2. Inspect its cart and approve its hash with the owner token. Save the returned
   permit in the owner workflow, never the agent context.
3. Call `checkout`; open its PayPal buyer-approval URL and log in as a sandbox
   personal buyer. The server's prototype return/cancel paths are not a UI;
   navigate back to the API client after approval/cancellation.
4. Call `authorize` with the owner token and permit after buyer approval.
5. For manual **simulated merchant fulfilment**, call `capture`. For cancellation
   before capture, call `void` instead.
6. If a payment outcome is unavailable, retrieve its operation ID from the audit
   and call `refresh`. Budget remains committed until the provider outcome is
   verified. This first version does not automatically recover every declined,
   expired, malformed, or externally changed payment; unresolved cases require
   operator investigation and must never be forcibly released.

The owner/payment workflow is separate from model tool calls. PayPal controls
buyer payment consent. The adapter cannot purchase at arbitrary outside merchants
and does not intercept existing subscription renewals. Renewals are represented
as protected commitments for the prototype.

Current documentation describes a 29-day authorization period and a three-day
honor period. The documented capture tolerance may exceed the original authorized
amount; GoalGuard explicitly supplies and checks the exact approved total.
These are documentation findings, **not verified sandbox observations**. The
local tests do not establish real honor-period behavior or expiry. PayPal's
delay-capture documentation specifically says sandbox authorizations do not expire
after 29 days and directs developers to negative testing.

- [Authorize and delay capture](https://developer.paypal.com/checkout/delay-capture/)
- [Authorization timing and capture limits](https://developer.paypal.com/payment-methods/auth-honor/)
- [Void an authorization](https://developer.paypal.com/api/payments/v2/authorizations-void/)

## Frozen next-stage scope

The local foundation is implemented. The remaining demo work is:

1. Retain the passed sandbox lifecycle as a regression baseline. Additional live
   failure scenarios require separate verification; the controlled reply-loss
   observation does not replace a real-provider process-kill test.
2. Connect two real agents to the same proposal/budget tools with separate tokens.
3. Add an owner review view with clear plan, reservation, authorization, and
   settlement labels; label synthetic catalog and manual fulfilment on screen.
4. Run the live LLM comparison in `EVALUATION.md`, retaining failures and successes.
5. Conduct five user conversations; record quotes only with consent.

Exclude model payment authority, real retailer coverage, forecasting, automatic
renewal interception, elaborate revocation, marketplace settlement, automatic
refund processing, and sophisticated policy migrations from this prototype.

This repository is ready to continue locally. It has not been published, hosted,
or submitted to the hackathon.

## Agent engineering framework

`prompts/shopping-agent.txt` is the initial minimal prompt. `prompts/experiments.json`
defines bounded recovery and fair ablations. These are prepared for the next agent
stage; they have not been executed with live models and are not runtime enforcement.
Financial controls remain in code. Prompt changes will be adopted only after
measured comparison of legitimate completion, violations, recovery, latency and cost.

The reusable skill package is in `skills/goalguard-engineering`. It is designed for
explicit invocation, with a short procedure and separate payment/agent references.
Its leading labels are Scope, Observe, Enforce, Verify, Recover, and Prune. It has
passed the skill validator. This folder is a bundled package, not a global skill
installation. To use it directly, ask the agent to read its `SKILL.md` for the
requested milestone. Installation into a discovery directory can be done later.
