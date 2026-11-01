# Denial recovery

| Result | Action |
|---|---|
| `budget_exceeded` with a counteroffer | Check its features against the user's request before using the one revision. Its availability is a quote, not a guaranteed reservation. |
| `budget_exceeded` without a suitable alternative | Explain that no suitable proposal was reserved. Do not silently drop a required feature. |
| `plan_required`, `plan_not_ready`, `policy_changed` | Hand off to the owner to confirm/update the plan. Do not ask for private bill or savings records. |
| `proposal_limit`, host revision/call limit | Stop. A fresh run does not reset the server quota. |
| `invalid_cart`, `unknown_product`, `invalid_proposal` | Correct the SKU/quantity shape from the catalog within the remaining proposal allowance. Do not supply a price, merchant override or approval flag. |
| `pending` / `outcome_unknown` | Only retry the identical proposal through the host. Do not replace an uncertain cart; it may already have reserved capacity. |
| `forbidden`, `unauthorized`, `internal_error` | Stop and ask the operator to inspect the connection/status. Do not try an owner action or another identity. |

Only purchase-specific status and limited denial information are available. Tool results do not expose the owner's full financial position.
