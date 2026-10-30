# Combined real-provider demonstration: proposed scope

Prepared 29 October 2026. **Awaiting scoped owner authorization.** UI acceptance
does not by itself authorize new provider calls. No model or payment provider
was called during preparation. No app implementation change is proposed here.

## Run boundary

- One new synthetic household in a dedicated private state directory outside
  the checkout, proposed `/private/tmp/goalguard-combined-20261029`. Create only
  if absent; otherwise inspect and resume it, never overwrite/reset it. Retain
  its database, signing key and operation identities until every payment outcome
  is verified. Do not use a temporary-directory context that deletes it at exit.
- Existing `.env.models` and `.env` remain private. Presence/required-field checks
  passed locally; account access, quota, billing tier and network access are not
  verified. No automatic model switch, paid fallback or billing change.
- At most one displayed synthetic-plan extraction and one shopping-agent run
  using configured model B: at most **10 model requests total**, including the
  caller's existing nine-request cap. The existing eight-tool-call, one-revision
  and persistent proposal quota controls remain intact. Stop on a provider error;
  no automatic replacement run.
- Exactly one owner-reviewed cart, **no more than USD $220 in PayPal sandbox
  test funds**, using the unchanged synthetic catalog. No production endpoint,
  real retailer checkout, real funds or private household records.
- At most one PayPal order and one authorization, followed by one exact-amount
  capture after manual demo fulfilment, or a verified void if cancelled. Permit
  ordinary OAuth and status reads needed for those actions. Do not blind-retry
  I/O or create replacement operations/orders to resolve an unknown result.
- Owner confirms the plan and exact cart in the UI; buyer login/approval remains
  manual. Credentials and consent permits never enter model context. If an
  authorization requires cleanup, retain state and verify its outcome.

## Reviewable sequence

1. Recheck the deterministic gates. Build the current frontend and launch a
   dedicated loopback server, proposed port 8772, using the private state and
   configuration above. Use a separate browser context. Keep existing servers
   and households untouched. Return/cancel URLs may point to this server's root
   for the run without editing the user's private configuration file.
2. The owner unlocks privately, reads the built-in sample, permits its model
   processing and requests one real initial draft. Record clarification/failure
   honestly and stop if it cannot produce a usable draft within this scope.
3. Owner reviews all extracted amounts/dates/obligations and confirms the exact
   preview. The expected sample calculation is $600 cash less a $100 bill,
   $50 buffer and the server-calculated savings contribution; actual displayed
   calculations, not this expectation, decide whether the plan is usable.
4. Run `agent.py` against that **same persistent state**, using only agent B's
   scoped token. Request one USB microphone with headphone monitoring; prefer
   the standard product and allow a suitable budget alternative. Do not use
   `agent.py --demo`: its disposable ledger cannot hand off a cart to checkout.

   ```sh
   python agent.py --agent agent-b \
     --state-dir /private/tmp/goalguard-combined-20261029 \
     --env-file .env.models --port 8772 \
     --request "Find one USB microphone with headphone monitoring. Prefer the standard model; a suitable budget alternative is acceptable. Propose it for owner review."
   ```

5. Verify actual SKU, quantity one, server-calculated amount at or below $220,
   reservation identity and remaining lifetime. A model's narrative is not a
   reservation. If the result violates scope, is denied, unavailable or expired,
   stop; do not silently start another model run. This single run is not a
   two-agent, concurrency, denial-recovery or reliability benchmark.
6. Owner checks the cart and gives exact-cart consent. Create one sandbox
   AUTHORIZE checkout. Owner completes buyer login/approval manually. Do not
   inspect or record passwords/account details. Returning to localhost is not
   proof of approval; the owner workflow verifies provider order terms/status.
7. Authorize the exact cart. After explicit manual-demo-fulfilment confirmation,
   capture the approved amount once, or void a verified uncaptured authorization
   if cancelled. Unknown results retain commitments and use the original
   operation's status refresh. Session expiry requires unlocking again, not
   automatic replay. Reservation expiry is not extended.
8. Read the final local ledger and provider evidence. Verify one capture counted
   once (or a verified void), current committed capacity and matching audit
   events. An order marked COMPLETED alone is not capture evidence. Keep all
   unresolved state and stop if observations disagree.

The lifecycle is consistent with PayPal's
[authorize/capture guide](https://developer.paypal.com/v5/checkout/auth-capture)
and [Payments v2 reference](https://developer.paypal.com/docs/api/payments/v2/),
checked during preparation. Long-duration/provider production behavior is not
part of this run.

## Evidence and stopping point

Keep raw run records and provider identifiers private; publish only separately
reviewed sanitized evidence. Record actual configured model/version, requests,
failure or clarification, selected cart, owner confirmation steps and verified
payment outcome. Keep synthetic catalog and manual fulfilment labels visible.
No success rate, second-vendor compatibility or sponsor eligibility is implied.

This authorization would not cover extra trials, a second agent/vendor, benchmark
matrices, live money, deployment, uploading a video, Devpost submission, committing
or pushing. Postman already has separate local evidence; APIMatic OAuth remains
unresolved and is not required to attempt this combined path.
