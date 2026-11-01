# Roadmap

## Implemented

- Owner-confirmed calendar-month plans with separate bills, buffer and savings goal.
- Actual-cash allocation, separate forecast and a bill horizon through next income.
- Atomic reservations, expiry, exact-cart consent, durable payment intents and audit.
- Safe financial revisions, paired external events, manual received refunds and rollover.
- Scoped proposal API, privacy allowlists, proposal quotas and bounded dispatcher.
- Sandbox adapter with recorded authorize/capture, authorize/void, retry and refresh evidence.
- Local enforcement checks, recorded-response regressions and a synthetic probing experiment.

## AI integration

- Implemented: Gemini adapter, scoped loopback client, bounded model loop,
  discoverable proposal skill and private transcript CLI. Two real Flash-Lite
  callers demonstrated shared-budget denial/recovery in one sequential scenario.
  Earlier incomplete Flash attempts remain documented. See [setup](agents.md)
  and [observed runs](../reports/gemini-demo.json).
- Verify a second model/vendor configuration; current demonstrated callers share one model.
- Repeat selection/recovery scenarios and adversarial cases; one observed scenario is complete.
- Implemented initial plan drafting; one actual Flash-Lite extraction of synthetic
  text saved a validated draft without activation. Code computed the contribution
  and available cash. Repeated/messy-input live evaluation remains pending.
  See [drafting](plan-drafting.md) and [evidence](../reports/plan-draft-demo.json).
- Record model IDs, prompts, tool transcripts, completion, failures, latency and cost.

## Owner experience

- Approved: React + TypeScript + Vite over the existing backend, with frontend
  lint, explicit typecheck, tests and build. Tooling scaffold is prepared in
  [frontend](../frontend/README.md); installation, four setup checks, lint/typecheck,
  coverage and build previously passed locally. CI/hook configuration is present;
  two new dependency guards now pass after the targeted Vitest 4.1.12 update,
  and the complete six-test frontend gate passes. The owner install-time audit
  reported zero vulnerabilities. Subsequent hosted verification is recorded in
  [browser CI repair](../agent_docs/browser-ci-repair.md).
- Initial connected owner screens are implemented: manual plan setup with
  preview/confirmation, exact-cart purchase review, and the audit timeline.
  Built assets are served by Python on the API origin. Browser inspection used
  disposable synthetic data, including keyboard exact-cart approval and its
  timeline event; it did not make a provider request.
- Implemented backend owner sessions and request protection: fixed 30-minute
  in-memory sessions, opaque HttpOnly/Strict cookies, logout/restart invalidation,
  session-bound CSRF and expected Origin/Host checks. Handler and TCP tests cover
  them. Frontend unlocking, logout, fixed expiry, form retention and deliberate
  retries are implemented, including protection against late session replies.
- Agreed: re-unlock on expiry, independent of durable payment state; light,
  restrained dashboard styling is implemented. The compact browser viewport and
  a keyboard approval path were inspected; broader device/accessibility review remains.
- Payment controls show separate buyer approval, authorization, manual-fulfilment
  capture, void and uncertain-operation refresh. Their interaction tests use
  fixtures; a complete new owner-browser-to-PayPal sandbox demonstration is pending.
- Owner UI now includes optional initial AI drafting from displayed built-in
  synthetic text only, explicit model-processing consent, clarification/manual
  fallback and separate exact-plan confirmation. Real owner text is not accepted.
- Paired financial-event entry is now in the Budget screen: received income,
  bill payments, savings deposits, external cash corrections and received refunds.
  Review and confirmation precede recording. Lost responses preserve the same
  record identity and require a status read before deliberate retry; Timeline
  exposes the recorded amount/reference/ID for inspection after reload.
- Verify the connected owner forms with a real model in a separately scoped
  synthetic run; UI fixtures and simulated extraction are not live AI evidence.
- Hosted checks now pass Python 3.11/3.14, Frontend Node 24 and the Ubuntu 24.04
  browser gate. Linux references were captured and visually reviewed separately;
  native screen-reader and browser-zoom review remain open.
- Explicit synthetic catalog and manual fulfilment labels.

## Evaluation and submission

- Supporting sponsor tool verified: Postman CLI 1.80.0 ran the disposable
  synthetic API walkthrough, 18 requests/45 assertions passed. No model or
  payment provider calls; APIMatic authentication remains pending. See
  [tool walkthrough](../postman/README.md) and
  [competition requirements map](../agent_docs/competition-readiness.md).
- Compare restricted real agents with a fair single-model memory baseline and sequential controls.
- Run prompt ablations with fixed scenarios and published run counts.
- Validate the problem and interface with five consented user conversations.
- Verify the financial-plan integration through a new complete sandbox demonstration.
- Add provider final-failure classifications only when supported by verified behavior.
- Prepare a runnable judging build, a backup recording and a demo under three minutes.

Real retailer coverage, automatic savings transfers, bank aggregation, investment
advice, live-money use and autonomous model payment authority are outside the MVP.
