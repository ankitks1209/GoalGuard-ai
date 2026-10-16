# HTTP API

The API uses JSON and listens on loopback by default. Every request requires
`Authorization: Bearer <scoped token>`. Tokens identify the household and owner or
agent role; callers cannot supply their own household scope. Use `Content-Type:
application/json` on POST. State and financial errors generally return HTTP 409;
missing authentication returns 401, forbidden scope 403, missing resources 404,
unavailable provider 503 and unexpected internal failure 500. Responses are not cached.

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
All these routes use the existing owner bearer token. Agents receive `forbidden`
with no financial fields. These are API routes; the owner interface is not built.

| Route | Method | Body |
|---|---|---|
| `/v1/plan` | GET | None; active plan plus last saved draft |
| `/v1/plan/preview` | POST | `plan`, `mode` |
| `/v1/plan/confirm` | POST | Same `plan`, same `mode`, returned `preview_hash` |
| `/v1/plan/cash-events` | POST | `event_id`, `kind`, `amount_cents`, `reference_id` |
| `/v1/plan/audit` | GET | None; private plan/cash history |

Modes are `activate`, `revise`, `rollover`. Preview saves a draft but grants no
purchase authority. Confirmation recalculates under `BEGIN IMMEDIATE` and binds
the preview to current policy, financial totals and affected purchases. Changed
obligations produce `stale_plan_preview`; obtain and review a new preview.

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
owner sessions/UI and user interviews are separate unfinished milestones.
