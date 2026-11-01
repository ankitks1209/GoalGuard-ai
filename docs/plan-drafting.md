# Owner text to a draft plan

**Status:** one real structured-output run succeeded on built-in synthetic inputs,
observed 21 October 2026. Gemini Flash-Lite returned a locally validated draft;
the owner API saved it without activation. See [sanitized evidence](../reports/plan-draft-demo.json).
This is separate from the shopping/recovery demonstration. Twelve
synthetic drafting cases now pass in the 206-case deterministic suite, including
owner-only access, input/output validation, source boundaries, contribution
calculation and no activation before confirmation. They are offline tests.

The helper extracts an **initial** plan from owner-written text. It cannot
activate a plan, revise existing obligations, approve a purchase or make a
payment. Manual plan entry remains available when interpretation fails.

## Browser demo

The Budget screen now exposes an optional, collapsed AI drafting section before
an initial plan is confirmed. The owner selected **synthetic/sample text only**.
It displays a fixed read-only USD sample with explicit dates and a separate
consent checkbox before sending that sample to `/v1/plan/draft`. Existing plan
records, manual form entries and credentials are not part of the model input.
Google's free-tier data-use notice is shown before consent.

A ready draft fills the manual editor and exact preview. The owner can correct
it, obtain a fresh preview after editing, and separately confirm. Clarification,
unavailable providers and invalid responses leave manual entry available; requests
never retry automatically. Locking clears consent/preview and discards late replies.
Model configuration remains server-side and optional. These browser checks use
synthetic responses or simulated extraction, not a new live-model observation.

## Try the synthetic demonstration

Use the existing Gemini configuration; the helper selects `GEMINI_MODEL_B`, the
Flash-Lite model demonstrated by the shopping callers:

```sh
python3 draft_plan.py --demo
```

This makes one real extraction request from built-in synthetic text. Trusted
setup starts a fresh disposable owner API and calls `/v1/plan/draft`, then reads
the plan status. It does not load PayPal configuration or existing runtime data,
and never calls confirmation. Private results are saved as `0600` JSON under
`.local/plan-drafts/`, excluded from Git. The temporary ledger is discarded.

Observed readback from the first run (one scenario, not a reliability rate):

- $600 cash, $100 unpaid bill, $50 buffer.
- $600 savings target with $300 already saved and three calendar-month installments.
- Code suggests $100 per period; $350 discretionary cash remains.
- `draft_saved: true`, `active_plan_created: false`, `confirmation: not_requested`.

The observed run used Gemini 3.5 Flash-Lite, reported 691 total tokens (469 input,
222 output), and took 16.683 seconds for the whole CLI workflow. This duration
includes setup/local HTTP; provider-only latency and billing cost are not known.
No owner confirmation, shopping proposal or PayPal call occurred.

The script generates explicit current dates. A clarification or provider error
is retained as that result; it is not converted into a successful draft.

## Owner API

Start the existing server with `.env.models` or an explicit model file:

```sh
python3 server.py --model-env-file .env.models
```

Model configuration is optional. Invalid/missing model configuration disables
drafting without preventing manual preview/confirmation. Keep the existing
state directory for a persistent household; do not reset it to create a new plan.

`POST /v1/plan/draft` requires the **owner** bearer token and exactly:

```json
{
  "request": "I have $600 cash and want a $50 buffer. My next expected income is $400 on 2026-10-25. I have no bills and no savings goal.",
  "timezone": "UTC",
  "currency": "USD",
  "allow_model_processing": true
}
```

Dates above illustrate the contract; use the actual intended dates. Explicit
model-processing consent is required before sending the supplied text. Existing
financial records, tokens, signing keys and payment credentials are never added
to the model request. This owner feature is absent from shopping-agent tools;
agents are rejected before a model call.

Responses:

| Status | Meaning |
|---|---|
| `draft_ready` | A locally validated draft and deterministic preview await owner review; this grants no spending authority |
| `needs_clarification` | Fields are missing, conflicting or unsupported; answer the questions or use manual entry |
| `needs_manual_entry` | Currency or model-output validation prevents a usable draft |
| HTTP 503 with model error code | The provider call did not complete; manual preview/confirmation remain available |

A ready draft includes `plan`, `preview`, `calculation`, `computed_fields`,
`requires_owner_confirmation`, model metadata and usage. A preview can still
have `activation_blocked_by` for insufficient cash, missing income information
or another existing financial rule. `draft_ready` means ready **for review**.

The owner checks all amounts, dates, bill completeness and the suggested savings
contribution. To activate, submit the reviewed exact plan to the existing
`/v1/plan/confirm` route with `mode: activate` and its preview hash. If edited,
obtain a fresh `/v1/plan/preview` first. Confirmation recalculates under the
ledger lock; a stale preview or infeasible plan cannot bypass those controls.
An existing active plan returns `draft_initial_only`; use its explicit manual
revision/rollover controls.

## What the model and code each do

The model selects relevant **literal quotes** from the text into a bounded JSON
schema. Local code rejects extra fields and wrong types, checks quoted values
against the original input, parses numeric USD amounts with decimal arithmetic,
validates dates, then uses the existing financial engine for the suggested
contribution and totals. Model output is never an approval flag.

When no contribution was explicitly specified, code derives it through the
existing savings calculation and lists `goal.contribution_cents` under
`computed_fields`. Generic names/IDs can be assigned by the host; no financial
amount is defaulted from missing information. Explicit statements are required
for no bills, no income or no savings goal. Missing current savings is not
silently treated as zero.

Limits: USD only, at most 4,000 input characters, twenty extracted bills, explicit
numeric money literals and YYYY-MM-DD dates, one model request, 4,096 output
tokens. Relative dates, currency conversion, arithmetic written in words and
plan revisions use clarification/manual entry. The complete manual API still
supports its documented larger bill limit.

Quote checks do not prove that the model assigned each number to the correct
meaning or included every obligation. **Owner review remains required.** The
raw request/extraction is not saved in the server database or ordinary logs;
only the normal validated plan draft is saved. The synthetic CLI's explicit
private record additionally retains its demonstration text/results.

Google's free-tier data terms apply to owner text submitted to Gemini. The UI
must explain this before consent; use synthetic data for this prototype's demo.
See [Gemini structured output](https://ai.google.dev/gemini-api/docs/structured-output)
and [pricing/data-use information](https://ai.google.dev/gemini-api/docs/pricing).
