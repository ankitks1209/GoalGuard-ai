# Verification reports

These are selected evidence snapshots. The test and experiment commands can also
write to a temporary path when you do not want to update a committed snapshot.

| File | Meaning |
|---|---|
| [local-checks.json](local-checks.json) | Deterministic suite, failures/skips, TCP cases and execution provenance |
| [budget-probing.json](budget-probing.json) | Synthetic attack parameters, denominators, per-run transcripts and provenance |
| [paypal-sandbox.json](paypal-sandbox.json) | Actual sandbox outcomes plus explicitly labeled local guards/injected faults |
| [gemini-demo.json](gemini-demo.json) | Four actual sessions: two incomplete Flash attempts, one Flash-Lite reservation, then two scoped Flash-Lite callers with sequential denial/recovery |
| [combined-demo-2026-11-03.json](combined-demo-2026-11-03.json) | Real Gemini proposal, exact-cart consent and verified PayPal sandbox order. Buyer checkout stopped at a currency error |
| [plan-draft-demo.json](plan-draft-demo.json) | One actual synthetic-input model extraction; draft saved, no activation or payment; original metadata caveat retained |
| [postman-demo.json](postman-demo.json) | Actual Postman CLI run: 18 synthetic API requests and 45 assertions passed; no model/payment provider calls |
| [owner-ui-demo.json](owner-ui-demo.json) | Built UI against actual local sessions/CSRF/ledger: simulated extraction, separate plan confirmation and two paired financial records; no model/payment providers |

```sh
python evaluate.py --report reports/local-checks.json --require-tcp
python probe_evaluate.py --report reports/budget-probing.json
```

New local reports record UTC capture time, Python version, command, source revision
and source-tree dirtiness. The dirty check excludes `reports/` so writing an
evidence snapshot does not itself mark the source as changed. The source revision
can precede the commit that saves the report. Missing historical metadata is
marked unknown rather than reconstructed as an execution fact.

PayPal observations retain their original observation timestamps and date. Their
provenance points to the first committed evidence, not a newly executed sandbox
run. The original unverified list describes the scope of that observation;
later financial-plan work has only local verification so far.
Raw OAuth responses, credentials and private account/resource identifiers are
excluded. Fixtures remain under `tests/fixtures/paypal-sandbox/` because regression
tests consume them.

CI publishes separate per-Python artifacts. Its local checks never call a live
payment/model provider. See [evaluation methods and limitations](../docs/evaluation.md).
