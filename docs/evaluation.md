# Evaluation and evidence

GoalGuard separates local enforcement checks, recorded-provider response replay,
actual sandbox observations and future live-model experiments.

| Evidence | Current scope |
|---|---|
| Local suite | 155 passing cases, zero failures/errors/skips; eight real loopback TCP cases |
| Financial semantics | 43 cases covering plans, goal arithmetic, cash records, revisions, rollover and privacy |
| Recorded PayPal replay | Four offline regressions using sanitized responses from the actual sandbox run |
| Actual sandbox | Authorize/capture, authorize/void, same-key replay and controlled reply-loss recovery |
| Synthetic probing | One deterministic scenario, ten capacities, two quota settings, 20 runs |
| Live models, baseline and ablation | Not run |
| User validation | Not conducted |

The local snapshot is a recorded result, not a claim that every future revision
passes. Workflow artifacts and committed [reports](../reports/README.md) identify
their source revision and environment where available. CI runs the local suite,
probe, demo, distribution build and installed-wheel smoke checks without provider
credentials. A successful CI run does not establish live PayPal/model behavior.

## Reproduce local checks

```sh
python evaluate.py --report reports/local-checks.json --require-tcp
python probe_evaluate.py --report reports/budget-probing.json
python demo.py
```

The enforcement suite uses temporary SQLite files, injected clocks, fixtures and
local TCP. It covers simultaneous reservations, duplicate keys, exact-cart consent,
TTL boundaries, scope enforcement, interrupted payment recovery and financial
revisions. Threaded tests deliberately share one database file. Three process-kill
cases use a durable simulated provider; they are not real-provider crash tests.
The financial suite covers the month-end rent boundary, payday inclusion, forecasts,
paired cash events, deficits, revision/authorization races and carried obligations.

## Actual PayPal sandbox observation

Observed 17 October 2026, Asia/Kolkata (16 October UTC), before financial-plan
integration. See [structured results](../reports/paypal-sandbox.json) and the
29 [sanitized response fixtures](../tests/fixtures/paypal-sandbox).

- OAuth: HTTP 200; no token response saved publicly.
- Create AUTHORIZE order: HTTP 200, `PAYER_ACTION_REQUIRED`.
- Genuine manual buyer approval: independently verified by GET `APPROVED`.
- Authorization: HTTP 201; Order `COMPLETED`, nested authorization `CREATED`, no capture.
- Exact $1 capture: HTTP 201, `COMPLETED`.
- Same-key capture replay: HTTP 200, same capture ID/amount, no second capture.
- Normal completed gateway retry: zero new provider calls.
- Separate $1 authorization/void: HTTP 200 with a `VOIDED` representation;
  subsequent GET independently confirmed `VOIDED`, releasing its local reservation.
- Altered cart of 101 versus 100 cents on the actual authorization: local ledger
  guard rejected before payment I/O; a preceding GET is excluded from that count.
- Deliberately suppressed successful authorization reply: local state retained
  100 cents in `reconcile_pending`; real status refresh restored `authorized`;
  the authorization was then voided.

Two isolated test ledgers began at 1000 cents each. The capture case ended with
100 spent, zero reserved and 900 available. The void case ended with zero spent/
reserved and 1000 available. No known authorization holds remained from those
scenarios. The earlier unapproved checkout was released locally.

Reply loss was deliberately injected after a successful actual response. It was
not a natural timeout or process kill. Resource IDs are consistently aliased,
account data is redacted and approval query tokens are stripped. Replaying these
fixtures is not another live run. Honor periods, long-duration expiry, provider
overcapture allowances and production behavior remain unverified. The later
financial-plan integration still needs a fresh complete sandbox demonstration.

## Synthetic budget probing

The attacker knows a 0–100 cent domain and adapts proposals in a one-cent catalog.
Accepted reservations stay counted; no cancellation/reset tool is available.
Across ten fixed capacities, the three-proposal cap permitted 0/10 exact recoveries;
the 32-proposal control recovered 10/10. No quota bypass occurred. For 73 cents,
three proposals narrowed the original capacity to 62–74 cents before a block.
Partial inference remains possible, and agents can combine observations. This
experiment uses a legacy aggregate test household, not a live model or private data.

## Planned real-model comparison

Keep model payments mocked and retain successful baseline behavior as well as
failures. Record provider/model/version, prompt, tool schema, configuration,
request scheduling, outputs, tokens, latency and exact run counts.

Compare independent per-purchase checks, a single model maintaining a budget
with disclosed shared-memory/concurrency semantics, and the same model using
GoalGuard. Include sequential updated-budget controls. Proposed first batch:
three scenarios (concurrency, injected description, feasible recovery), ten
repetitions, three comparisons, plus ten sequential controls: 100 planned runs.
These are targets, not completed evaluations.

Measure accepted violations, legitimate completion, false denials, recovery,
unresolved outcomes, latency and cost. Prompt ablations change one reasoning
instruction at a time under identical permissions; deterministic controls stay
fixed. Report specific observed behavior rather than a universal safety claim.
