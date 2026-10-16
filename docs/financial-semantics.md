# Financial semantics

## Money and period

Amounts are bounded integer USD cents. Fractional cents, booleans as money and
other currencies are rejected. PayPal amounts use exact decimal strings.
The owner confirms an IANA timezone. The first reporting period starts at
activation and ends at the next calendar month; period end is exclusive.
Currency and timezone do not change during revisions or rollover.

Opening cash is a self-reported spending pool before this plan's commitments.
It excludes separately held savings and already reflects historical activity.
Purchases and external events after activation are counted once. No bank
connection, automated bill payment or real savings transfer exists.

## Protection and cash authority

```text
bill_cutoff_exclusive = max(period_end, start_of_day(next_income_date + 1 day))
protected_bills = unpaid bills due before the cutoff, including overdue bills
cash_base = opening_cash + confirmed_inflows - recorded_external_outflows
protected = protected_bills + buffer + remaining_goal_contribution
available_now = cash_base - protected - captured_spend - active_reservations
projected_surplus = available_now + expected_unreceived_income
```

The cutoff includes bills due on payday because an arrival time is not guaranteed.
On 30 October, $500 cash and $400 rent due 1 November with income expected
5 November leave $100 for purchases. A $150 proposal is denied.

Expected income affects only the forecast. Missing next-income information or an
overdue unreceived receipt blocks new purchases. Partial receipt reduces the
forecast remainder. Once fully received, the owner must confirm the next expected
payday before new purchases so a stale date cannot shorten future protection.

Drafts with a negative forecast are `infeasible`; negative availability with a
nonnegative forecast is `waiting_for_income`. Neither can activate purchasing.
Zero discretionary capacity can be confirmed explicitly. Actual external
corrections can reveal negative availability in an active plan; show the deficit,
block new reservations and retain all captured/uncertain obligations.

## Savings schedule

```text
remaining = max(target - current_saved, 0)
N = calendar months through deadline month, inclusive
suggested_contribution = ceil(remaining / N) in cents
```

The partial first month counts in full and assumed investment return is zero.
A past deadline for an unfinished goal is invalid. The owner confirms the
contribution; a smaller override is labeled off-track. An installment is capped
at the remaining target. A month-level projection does not guarantee that income
will arrive before a mid-month goal deadline.

Earmarking a contribution is not a deposit. Recording an actual external savings
deposit atomically decreases cash, fulfills the period installment and increases
the saved balance. An excess deposit uses extra cash; fulfillment cannot create
additional capacity below zero contribution. The fixed installment and original
schedule are not recalculated after each deposit.

## External events and refunds

Each owner-confirmed external event has a unique household-wide ID. Identical
retries do not move the balance again; a changed payload under the same ID is
rejected. Bill payment decreases cash and unpaid protection together in one
transaction. Savings deposits pair all three corresponding changes.

A received refund is a cash inflow linked to a captured purchase. Keep the
original capture in spending; do not also reverse it. Total recorded refunds
cannot exceed the captured amount. Automatic refund processing is not implemented.

## Revisions and consent

Title-only and expected-income-amount-only edits preserve approval. Other
financial changes advance the policy version and release all pre-payment
reservations in one write transaction. The owner preview lists affected purchases.
Opening cash cannot be edited after activation; record an explicit cash correction.

Approval and authorization initiation check the current plan/version under the
same write lock. A previously created provider order cannot bypass invalidation.
Verified authorizations retain their original consent/cart/amount for later
capture or void, including after policy changes. Financial revisions wait while
payment I/O is in flight or its outcome is uncertain. Actual external events
can still be recorded during uncertainty without releasing payment obligations.

## Rollover

At period end, stop new purchases until the owner confirms the next plan.
Rollover is blocked by in-flight or uncertain payments.

```text
next_opening_cash = old_cash_base - old_captured_spend
```

Carry every unpaid bill ID with its remaining amount and due date, preserve
recorded savings, and confirm the next buffer/contribution/income. Verified
authorizations move to the new plan once, keeping original payment terms and
audit links. Historical captures stay with the old plan, already reflected in
new opening cash. Existing pre-payment approvals are released.

Initial plan activation rejects aggregate-only legacy households that already
have captured, authorized or uncertain payments. Their opening-cash basis requires
an explicit migration; the system never resets obligations or rotates keys to
make activation succeed. See [API](api.md) and [evaluation](evaluation.md).
