# HTTP API

The API uses JSON and listens on loopback by default. CLI/agent requests use
`Authorization: Bearer <scoped token>`; owner browser requests use the local session
below. Tokens identify the household and owner or agent role; callers cannot
supply their own household scope. Use `Content-Type:
application/json` on POST. State and financial errors generally return HTTP 409;
missing authentication returns 401, forbidden scope 403, missing resources 404,
unavailable provider 503 and unexpected internal failure 500. Responses are not cached.

## Local owner browser sessions

| Route | Method | Authentication and body |
|---|---|---|
| `/v1/owner/session` | POST | Existing owner bearer token; `{}` |
| `/v1/owner/session` | GET | Owner session cookie; no body |
| `/v1/owner/logout` | POST | Owner session cookie and CSRF token; `{}` |
| `/v1/owner/overview` | GET | Owner session cookie or owner bearer token; no body |

Session exchange requires `Content-Type: application/json`, the expected `Host`
and an `Origin` exactly matching `http://<Host>`. With the IPv4 loopback listener,
the accepted hosts are `127.0.0.1` and `localhost` at its actual port. Forwarded
headers do not establish the expected origin. Agents cannot exchange their tokens
for owner sessions. The exchange sets `goalguard_owner_session` with `HttpOnly`,
`SameSite=Strict`, `Path=/` and `Max-Age=1800`; its value is a random identifier,
never the owner token. HTTP is limited to this local development design.

Exchange and session status return `csrf_token` and `expires_in_seconds`. Keep the
CSRF token in memory and send it as `X-CSRF-Token` on every cookie-authenticated
POST, including logout. Such requests also require JSON and expected Origin/Host;
when present, `Sec-Fetch-Site` must be `same-origin`. A CSRF token from another
session is rejected. Missing/expired sessions return 401; request-protection or
role violations return 403. Session status does not extend the fixed 30-minute
lifetime. Logout revokes that session and clears its cookie; server restart
invalidates all sessions. Unlocking again rotates any presented session cookie.

Existing non-browser bearer clients remain supported. Browser-marked POST requests
(`Origin`, `Sec-Fetch-Site` or `Cookie` present) cannot use bearer authentication to
bypass CSRF; token exchange is the sole exception and validates Origin/Host itself.
After unlocking, use the cookie alone for authentication.

Expiry, logout and unlocking do not change ledger commitments or replay requests.
The interface retains non-secret form input in memory and requires deliberate
retry after unlocking. Late mutation replies are discarded if the session changes;
an old 401 cannot lock a newly unlocked session.

Overview returns the current `plan`, saved `draft`, household-scoped `purchases`
and a combined `events` timeline. Purchases include their stored cart, latest
`operation_id`, and existing `permit` for resuming consented payment steps. This
does not mint a permit or grant new consent. The owner-only role check precedes
all financial reads; agents cannot access this projection. Keep the response and
its permits out of model context and persistent browser storage. Separate reads
can age between requests; preview/confirmation/payment code remains the authority.

Run `npm --prefix frontend run build` before starting `python server.py` from a
source checkout. The server serves only the built index and files below its
`frontend/dist/assets` directory, on the same origin as `/v1/`. Source files,
credentials and traversal outside the build root are not served. The Vite dev
server is a separate appearance preview; it has no proxy to the owner API.
The source-checkout owner interface has manual plan preview/confirmation,
optional initial AI drafting from built-in synthetic text with explicit consent,
paired financial-event records, exact-cart purchase review and a timeline.
Real financial text is not accepted by the browser's AI demo. The existing
API/CLI contract does not authorize sending private owner records to a model.

## Catalog, proposals and payment lifecycle

| Route | Method | Scope | Body |
|---|---|---|---|
| `/v1/catalog` | GET | Agent/owner | None |
| `/v1/budget` | GET | Owner full; agent coarse floor | None |
| `/v1/proposals` | POST | Agent | `items`, `request_key` |
| `/v1/purchases/{id}` | GET | Proposing agent/owner | None |
| `/v1/purchases/{id}/audit` | GET | Owner | None |
| `/v1/purchases/{id}/approve` | POST | Owner | `cart_hash` |
| `/v1/purchases/{id}/release` | POST | Owner | `{}` |
| `/v1/purchases/{id}/checkout` | POST | Owner | `{}` |
| `/v1/purchases/{id}/authorize` | POST | Owner | `permit` |
| `/v1/purchases/{id}/capture` | POST | Owner | `permit` |
| `/v1/purchases/{id}/void` | POST | Owner | `permit` |
| `/v1/purchases/{id}/refresh` | POST | Owner | `operation_id` |

```json
{"items":[{"sku":"mic-standard","quantity":1}],"request_key":"recording-001"}
```

Only SKU and integer quantity are accepted per item; the server determines
merchant, price, currency and delivered total. A repeated key must keep the same
cart. The default quota is three distinct proposals per agent per plan period,
including denials. Default model tools omit the optional budget route.

A reservation requires owner confirmation of a current funded financial plan.
An insufficient-budget result returns `decision: denied`, `reason: budget_exceeded`
and at most one feasible counteroffer with catalog items, total and
`requires_new_proposal: true`. No financial records or exact balance are disclosed.
A revised cart needs a new request key and fresh reservation. An uncertain
transport result retains the old key for an idempotent retry.

Owner approval returns a signed `permit` binding exact terms. It is an authority
credential and must remain outside model context. Checkout creates the PayPal
buyer-approval URL. The owner completes approval manually before authorization;
capture represents manual demo fulfilment. Void cancels an uncaptured authorization.
Unknown outcomes stay committed until status refresh. See [PayPal setup](paypal-setup.md).

## Financial plan routes

The loopback server requires an owner-confirmed plan before accepting purchases.
These routes accept the owner bearer token or protected owner session. Agents receive `forbidden`
with no financial fields. The owner interface connects manual preview and
confirmation, the restricted synthetic AI demo and paired cash-event entry.

| Route | Method | Body |
|---|---|---|
| `/v1/plan` | GET | None; active plan plus last saved draft |
| `/v1/plan/draft` | POST | `request`, `timezone`, `currency`, `allow_model_processing: true`; initial plans only |
| `/v1/plan/preview` | POST | `plan`, `mode` |
| `/v1/plan/confirm` | POST | Same `plan`, same `mode`, returned `preview_hash` |
| `/v1/plan/cash-events` | POST | `event_id`, `kind`, `amount_cents`, `reference_id` |
| `/v1/plan/audit` | GET | None; private plan/cash history |

Modes are `activate`, `revise`, `rollover`. Preview saves a draft but grants no
purchase authority. Confirmation recalculates under `BEGIN IMMEDIATE` and binds
the preview to current policy, financial totals and affected purchases. Changed
obligations produce `stale_plan_preview`; obtain and review a new preview.

The optional model-backed draft route extracts only the supplied owner text;
it does not activate a plan. A valid result includes a normal preview and requires
separate owner confirmation. Missing/conflicting facts yield clarification;
provider failure leaves manual entry available. Shopping agents cannot access it.
See [drafting contract, consent and limits](plan-drafting.md). One historical
synthetic-input live extraction exists; a fresh browser-to-model run is pending.

### Plan input

Generate a synthetic plan with current dates using:

```sh
python3 -B demo.py --write-plan /tmp/goalguard-demo-plan.json
```

The file contains only synthetic data. The demonstration itself uses isolated
temporary state, simulated callers and no PayPal or LLM requests.
For the running API, wrap that JSON as the `plan` field:

```json
{
  "mode": "activate",
  "plan": {
    "title": "Household plan",
    "timezone": "UTC",
    "currency": "USD",
    "opening_cash_cents": 60000,
    "buffer_cents": 5000,
    "next_income": {"id": "pay-1", "due_date": "2026-10-20", "amount_cents": 40000},
    "bills": [{"id": "utilities", "name": "Utilities", "amount_cents": 10000, "due_date": "2026-10-25"}],
    "goal": {
      "id": "equipment", "title": "Equipment savings",
      "target_cents": 60000, "current_saved_cents": 30000,
      "target_date": "2026-12-31", "contribution_cents": 10000
    }
  }
}
```

Dates above illustrate the schema; use current dates when running it. The owner
explicitly confirms the contribution, including any off-track override. `goal`
may be null; `bills` may be empty. `next_income: null` saves a draft requiring a
date, with no activation. Currency is USD, amounts are integer cents, dates are
YYYY-MM-DD, IDs/labels are nonempty and bounded, and duplicate bill IDs are rejected.
The active period starts at confirmation and ends at the next month in the
confirmed IANA timezone. Timezone and currency are immutable on revisions/rollover.

### Financial semantics

```text
cash_base = opening_cash + recorded_cash_inflows - recorded_external_outflows
protected = unpaid_bills_through_cutoff + buffer + remaining_goal_contribution
available_now = cash_base - protected - captured_spend - active_reservations
forecast = available_now + expected_unreceived_income
cutoff_exclusive = max(month_end, next_income_date + 1 day)
```

Opening cash excludes separately held savings and already reflects historical
transactions. New spending requires nonnegative actual availability. Expected
income never funds a reservation. Overdue bills are included; later bills are
visible without being deducted. A real cash correction can reveal a negative
balance; the ledger records it honestly and blocks new purchases, preserving
captured spending and all unresolved obligations.

Statuses: `ready`, `zero_capacity`, `infeasible`, `waiting_for_income`,
`needs_income_date`, `income_overdue`, `needs_next_income`, `rollover_required`.
Only ready/zero-capacity plans can be activated for purchasing. An unfunded initial
draft can be edited with newly confirmed opening cash before activation.
After the expected receipt is fully recorded, the owner must confirm the next
expected payday before new purchases; an old received payday cannot define the
future bill horizon. Partial receipts leave the rest in the forecast and remain
overdue after the expected date. Updating an expected amount alone cannot grant
new cash authority.

Savings suggestions use integer ceiling division of remaining target by inclusive
calendar months, with zero assumed return and the partial first month counted in
full. The fixed installment is capped at the remaining target. An earmark is not
a savings transfer. A recorded deposit reduces cash, increases saved balance and
fulfills the installment atomically; an extra deposit uses extra cash. Recording
a deposit never recomputes the fixed installment or its original schedule.

### Cash events

Record only activity the owner confirms has actually happened externally. These
routes do not move money or pay bills.

```json
{"event_id":"external-txn-001","kind":"savings_deposit","amount_cents":4000,"reference_id":"equipment"}
```

| Kind | Cash effect | Reference |
|---|---|---|
| `income` | Credit | Current expected receipt ID |
| `external_inflow` | Credit | null |
| `external_outflow` | Debit | null |
| `bill_payment` | Debit and reduce unpaid bill together | Bill ID; cannot overpay |
| `savings_deposit` | Debit, fulfill contribution, increase saved amount together | Goal ID |
| `refund` | Credit; original capture remains spent | Captured purchase ID; cumulative refunds cannot exceed capture |

An event ID is unique across the household, including rollover. Same ID/payload
returns the current summary without a second adjustment; changed payload rejects.
Actual events are recorded even during provider uncertainty. They invalidate
pre-payment approvals atomically but preserve any payment already started.

### Revisions and rollover

Title-only edits and expected income amount-only edits preserve approvals. Other
financial changes advance policy version and release all pre-payment reservations
in one transaction. The preview lists the affected purchase IDs. Opening cash
cannot be rewritten after activation; use an explicit cash event. Verified
authorizations survive revisions and can capture or void their original amount.
In-flight or uncertain payments block financial revision/rollover; title-only
changes do not erase them. Invalidated PayPal orders cannot start authorization.

At month end, new purchases stop until owner-confirmed rollover. Submit opening
cash equal to previous `cash_base_cents - spent_cents`; use every unpaid bill's
same ID/date and remaining amount, and preserve the goal's recorded saved balance.
Confirm the new buffer, contribution and next expected income. The next period
counts carried authorized purchases once. Old captures remain historical, already
deducted from new opening cash. Carry events link both plans in the purchase audit.
Proposal quotas use the active plan ID and do not reset on an in-period revision.

Existing aggregate-only test APIs remain for compatibility. First plan activation
refuses legacy households with captured/authorized/uncertain payments: migrating
their opening-cash basis needs a separate explicit migration. It never resets their
money or rotates the signing key. Use a fresh external state directory for the new
owner workflow rather than erasing existing payment state.

### Evidence and limits

Financial behavior is checked with controlled clocks, shared-file concurrent
writers and local HTTP. This is separate from the earlier real sandbox lifecycle.
External events are self-reported; no bank synchronization or real savings transfer
exists. Provider error classifications not yet established by evidence remain
pending rather than releasing funds. Real models, natural-language plan drafting,
broader model evaluation and user interviews remain separate milestones. Initial
owner sessions/UI have local evidence; the combined provider demonstration is pending.
