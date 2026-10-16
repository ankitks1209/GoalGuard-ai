# GoalGuard payment invariants

## Ledger

`available = budget - protected commitments - captured spending - encumbered purchases`.
Require non-negative available budget. Count each purchase once. Capture moves its
cost from encumbered to spent, so it does not restore capacity. Void/release/expiry
restore capacity only when no unresolved payment remains.

Acquire a database write transaction before checking and reserving. Real
concurrency checks use multiple threads/processes and independent connections to
one database file. A sequential loop is not concurrency evidence.

The internal pre-authorization hold has its own TTL. At or after the deadline,
deny new consent and initiation. Once authorization I/O starts, keep the budget
committed through unknown outcomes. Do not infer provider cancellation from local
clock expiry. An injectable clock should make deadline tests deterministic.

## Consent and credentials

Read current code before claiming these are implemented:

- Recompute price and cart from trusted catalog data; model descriptions are data.
- Bind approval to household, agent, merchant, cart, quantity, complete amount,
  currency, and initiation expiry. Bind the provider order when created.
- Use constant-time signature comparisons. Consume initiation consent atomically
  with its durable operation/state transition. Idempotent replay returns the same
  lifecycle; it cannot initiate a second payment.
- Keep signing keys and runtime tokens outside the source repo with restricted
  file permissions. Example configuration has placeholders, never working secrets.
- Agent credentials cannot approve, authorize, capture, void, or read another
  agent's purchase. Owner authority does not belong in model context.

## Provider lifecycle and recovery

GoalGuard budget reservations and PayPal authorizations track different facts.
Create an `AUTHORIZE` order, obtain genuine buyer approval, then authorize. The
gateway may capture or void only that approved lifecycle. Do not infer arbitrary
merchant purchasing authority from sandbox merchant credentials.

Before a money-moving call, commit an intent containing the operation/idempotency
ID, action, purchase, provider IDs, cart fingerprint and exact amount. Call the
provider outside that DB transaction. Record a verified result afterward. A crash
between these writes must retain the commitment and permit status reconciliation.

Verify order details and explicitly limit capture to the approved total even if
the provider allows a higher capture. Check current honor period, authorization
expiry and void rules in official docs; label documentation findings separately
from exercised sandbox behavior.

When testing crashes, kill only a subprocess launched for the test after a known
barrier. Distinguish a process-kill test with a simulated provider from a live
sandbox test. Never send a second money-moving call merely to discover whether the
first succeeded. Read status or reuse the persisted provider idempotency key in
an explicitly authorized recovery procedure.
