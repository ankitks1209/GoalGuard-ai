# GoalGuard sandbox verification gate

**Observed:** 17 October 2026, Asia/Kolkata (16 October UTC).
**Gate 2 core lifecycle: passed against actual PayPal sandbox.** No fallback used.

| Observation | Actual outcome |
|---|---|
| OAuth | HTTP 200; token received, never saved in public evidence |
| Create AUTHORIZE order | HTTP 200, `PAYER_ACTION_REQUIRED` |
| Manual buyer approval | Verified through GET order status `APPROVED`, not redirect parameters |
| Authorize | HTTP 201; Order `COMPLETED`, nested authorization `CREATED`, no capture |
| Exact $1.00 capture | HTTP 201, `COMPLETED`; spent 100 cents, reserved zero |
| Same-key provider capture replay | HTTP 200, same capture ID and amount; no second capture |
| Completed gateway retry | Cached result; zero additional provider calls |
| Separate authorization and void | HTTP 200 with `VOIDED` body; GET authorization independently confirmed `VOIDED` |
| Altered amount on actual authorized purchase | Local ledger guard rejected 101 versus 100 cents; zero provider calls during guard (a preceding GET is excluded) |
| Deliberately suppressed authorization reply | Real authorization succeeded; local state stayed `reconcile_pending`, retaining 100 cents; real status refresh restored `authorized`; then voided |

Two isolated ledgers began with 1000 cents capacity each. Final capture scenario:
100 spent, zero reserved, 900 available. Final void scenario: zero spent/reserved,
1000 available. No known authorization hold remains from these scenarios.
The earlier unapproved checkout was released locally, not represented as paid.

The lost-response fault was injected locally after a successful actual provider
reply; it was not a natural timeout or process kill. The altered-amount observation
exercises the ledger guard; the HTTP request-schema guard is covered separately
by local tests. No deliberately excessive capture was sent to PayPal.

Evidence: `sandbox-results.json`, 29 sanitized provider responses in
`tests/fixtures/paypal-sandbox/`, and four offline recorded-response regression
cases in `tests/test_paypal_recorded.py`. OAuth responses are excluded. Names,
account details, original resource IDs and approval query tokens are stripped or
consistently aliased. Replaying fixtures is not another live sandbox run.

Initial checkout displayed a currency error. A new US Personal sandbox buyer in
Chrome Incognito approved successfully using the existing IN seller. Both buyer
country and browser session changed; the exact earlier cause was not isolated.
The localhost return page refused connection because no callback server was
running. Approval was verified independently through PayPal's API.

Actual response shapes differ from the early fixtures: Order `COMPLETED` does
not mean captured; capture replay changed HTTP 201 to 200; void returned a full
HTTP 200 representation. The gateway already handles these cases. Its handwritten
authorization fixture now matches the observed Order status.
Honor periods, long-duration expiry and provider overcapture allowances remain
unverified. Real LLM experiments, owner UI and financial-plan semantics remain
unfinished. This gate is scoped prototype evidence, not production validation.

## Historical preflight (15 October, before credentials were supplied)

## Completed preflight

| Check | Result and scope |
|---|---|
| Merchant ID dependency | Required by current adapter: `create_order` sets `purchase_units[0].payee.merchant_id`; `validate_order` checks it against configuration |
| Credential readiness | Client ID, secret and merchant ID missing; return/cancel URLs present. Only booleans were printed |
| Git repository | Initialized an empty local repository; no commit or remote added |
| Ignore verification | `git check-ignore -v .env` returned `.gitignore:3:.env .env` |
| Tracked-file verification | `git ls-files --error-unmatch .env` failed as expected: .env is not tracked |
| Local overcapture check | Existing `test_overcapture_total_is_denied_locally` rerun: 1 passed. Ledger-level local check, not a live PayPal or HTTP observation |

Keep merchant ID for this gate. Removing the explicit payee and corresponding
validation would change the adapter contract; it is not merely deleting a setup
instruction. Check the matching Business sandbox account's details for a displayed
merchant ID first; if absent, use the documented sandbox seller account settings.

## Human approval and callback contract

The owner signs into each PayPal approval URL using the Personal sandbox buyer and
approves each new order manually. Do not automate buyer login or approval.
Never put the buyer password in model context, fixtures or logs.

The current localhost return/cancel URLs are placeholders, and the prototype has
no functioning owner callback page. A redirected localhost page may fail or show
an API error. Do not infer approval from that page or query parameters. Read order
status from PayPal, validate its bound cart/merchant/amount, then authorize through
the owner workflow. Genuine PayPal buyer approval is still mandatory.

## Ordered live run

Stop at the first unexpected result. Keep known authorizations and uncertain
operations recorded rather than resetting their ledger or issuing new requests.

1. **Token fetch.** Fetch an OAuth token to prove the client ID/secret. Report only
   HTTP outcome, token type and expiry; do not save the token response as a fixture.
2. **Order A: authorization.** Create an order with `intent=AUTHORIZE`. Save its
   redacted request/response. Hand the URL to the owner, wait for manual approval,
   read/validate order details, authorize with a durable operation ID and record
   the authorization. Keep this order distinct from capture and void branches.
3. **Order B: capture.** Create a new order, obtain new manual buyer approval and
   authorize it. Capture its exact approved total; confirm provider settlement and
   that reservation becomes captured spending without restoring capacity.
4. **Order C: void.** Create another order, obtain manual approval, authorize and
   void it. A 204/empty void response must be followed by verified authorization
   status `VOIDED` before budget release.
5. **Over-approved-total attempt.** Against a valid owner workflow, send an
   attempted amount override to the capture endpoint. Its strict schema accepts
   only the permit, so it must reject the added field before payment I/O. Instrument
   outgoing calls to prove zero new provider calls. Separately retain the local
   ledger test rejecting a cart whose total differs from consent. Do not actually
   send an overcapture request to PayPal to prove GoalGuard's guard.
6. **Provider idempotency replay.** Replay Order B's same capture method, endpoint,
   exact body and original `PayPal-Request-Id` within documented retention. Check
   resource identity/latest status and that no second capture is created. Also
   check a normal GoalGuard retry returns its stored result without provider I/O;
   these are different observations and must be reported separately.
7. **Lost-response reconciliation.** Use a separate order and manual approval.
   Persist the payment intent, then suppress a successful provider response before
   the ledger finish to simulate local response loss. Record the injection as
   simulated. Refresh real provider status, confirm one settlement/authorization
   and preserve capacity until the verified transition. This is not evidence of
   a naturally occurring network timeout.
8. **Cleanup.** Verifiably void any known authorization left by authorization-only
   or reconciliation scenarios. Keep unresolved outcomes pending. Captured orders
   remain captured; do not use void on them.

Use USD and confirm the buyer has USD test funds. The sandbox API base stays fixed
to `https://api-m.sandbox.paypal.com`. Public results identify manual fulfilment
and any locally injected faults explicitly.

## Evidence hygiene

Keep runtime state and any sensitive raw captures outside the source repository.
Publish only sanitized fixtures and their provenance after review.

- Strip Authorization headers, Basic/Bearer values, client secrets, tokens, buyer
  passwords, approval permits, session cookies and OAuth nonces.
- Remove payer/payee emails, names, addresses, phone numbers and account identifiers.
- Replace order/authorization/capture/merchant/request IDs with consistent aliases
  across the run. Rewrite IDs in links and remove approval-link query tokens.
- Preserve status, HTTP code, intent, amounts/currency, error name/details and link
  relation labels so schema differences remain inspectable. Redact free-text error
  fields if they contain account information. Do not hide surprising behavior.
- Preserve field structure rather than replacing an entire response with the shape
  the adapter expected. Mark empty responses explicitly with their HTTP status.
- Record timestamp, scenario, method/path, alias of request ID, observed response,
  local state before/after and whether a fault was injected. Never save auth headers.
- Review the staged fixture diff for residual private fields before committing.
  A .gitignore rule protects normal additions, not deliberate force-add or secret
  values copied into another tracked file.

## Results to paste after the run

For each step, provide tested/not-run, HTTP outcome, sanitized provider status,
amount/currency, local accounting change, and any unexpected response fields.
Separate actual sandbox observations, locally injected response loss and local
deterministic tests. Do not update live-PayPal evidence to passed until observed.

The ordered runbook above predates the run. The completed run consolidated
capture/retry into one approved order and authorization/controlled-fault recovery/
void into a second. Historical credential gaps are resolved; current results are
the observation table at the top, not the former preflight status.

## References

- [PayPal idempotency semantics](https://developer.paypal.com/api/rest/reference/idempotency/)
- [PayPal REST setup](https://developer.paypal.com/api/get-started/)
- [PayPal Orders API](https://developer.paypal.com/api/orders/v2/)
