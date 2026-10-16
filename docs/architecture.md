# Architecture

GoalGuard is a local Python backend with a SQLite ledger and a thin HTTP tool API.
It protects an owner-confirmed financial plan while shopping callers propose
purchases. The current callers are deterministic; real models are not connected.

```mermaid
flowchart LR
    Caller[Shopping caller] --> Tools[Scoped proposal API]
    Tools --> Catalog[Authoritative synthetic catalog]
    Tools --> Ledger[SQLite ledger and financial plan]
    Owner[Owner API client] --> Review[Plan confirmation and exact-cart consent]
    Review --> Ledger
    Owner --> Payments[Payment coordinator]
    Payments --> Ledger
    Payments --> PayPal[PayPal sandbox]
    Buyer[Buyer] --> Approval[PayPal approval page]
    Approval --> PayPal
```

## Modules

| Module | Responsibility |
|---|---|
| `goalguard/finance.py` | Validate dates, currency and money; calculate protection, savings installments and forecast |
| `goalguard/plans.py` | Owner preview/confirmation, separate bill/goal records, cash events, revisions and rollover |
| `goalguard/ledger.py` | Atomic reservations, consent signatures, expiry, durable payment operations and audit |
| `goalguard/catalog.py` | Server-owned prices and deterministic alternatives in the synthetic catalog |
| `goalguard/gateway.py` | Actor scopes, quota enforcement and payment coordination |
| `goalguard/agent_view.py` | Allowlisted public agent responses |
| `goalguard/runner.py` | Trusted dispatcher with an eight-call, one-revision limit; no live model adapter yet |
| `goalguard/paypal.py` | Fixed sandbox endpoint, provider calls and exact order/amount validation |
| `server.py` | Loopback HTTP transport, scoped development tokens and expiry sweep |

## Allocation and payment are separate

A local reservation reduces discretionary capacity before buyer approval. It is
not a PayPal funds hold. After buyer approval, PayPal authorization creates a
provider payment authorization. The same purchase stays counted once throughout.

```mermaid
stateDiagram-v2
    [*] --> Reserved
    Reserved --> Approved: Owner consent
    Reserved --> Released
    Approved --> Released
    Reserved --> Expired
    Approved --> Expired
    Approved --> Authorizing: Durable intent
    Authorizing --> Authorized: Verified provider result
    Authorized --> Capturing
    Capturing --> Captured
    Authorized --> Voiding
    Voiding --> Voided
    Authorizing --> ReconcilePending: Unknown outcome
    Capturing --> ReconcilePending: Unknown outcome
    Voiding --> ReconcilePending: Unknown outcome
    ReconcilePending --> Authorized: Verified authorization
    ReconcilePending --> Captured: Verified capture
    ReconcilePending --> Voided: Verified void
```

Pre-payment reservations expire 15 minutes after original reservation, including
at the exact deadline. Approval/retries do not extend the TTL. Once payment I/O
starts, a local deadline cannot release the obligation. Captured spending remains
deducted. See [financial semantics](financial-semantics.md).

## Transaction and recovery boundary

`BEGIN IMMEDIATE` serializes SQLite writers, including different households.
Quota claims bind to the active plan period; a period change before reservation
requires a same-key retry. Allocation and the current policy check happen under
the write lock. Financial revisions invalidate pre-payment approvals atomically.

Provider I/O happens outside the database transaction. Before it starts, the
ledger persists an operation with its original cart, amount and provider IDs.
Completed retries return the stored result; an uncertain result requires status
refresh. PayPal receives the operation ID as `PayPal-Request-Id`.
This is a single-instance prototype, not a horizontally scaled database design.

## Agent and owner authority

Agent tools expose catalog items, purchase proposals and redacted own-purchase
status. The server owns merchant, price and delivered total. Agents cannot supply
approval flags, owner credentials or payment amounts. Owner-only routes confirm
plans, grant cart-bound consent and execute payment actions.

Responses exclude bills, income, buffer, savings goals, owner audit, provider IDs
and consent permits. An optional legacy budget route returns a conservative $50
headroom floor; default model tools omit it. Counteroffers expose at most one
feasible catalog alternative, not the exact remaining balance.
Three distinct proposals per agent/plan period include denials. Same-key/same-cart
retries reuse a quota slot. Decision outcomes still permit partial inference.

## Implemented scope

The financial backend is locally verified. Core authorize/capture and
authorize/void flows have separate actual sandbox evidence. That observation run
predates the financial-plan integration. Model callers, natural-language plan
drafting, owner UI/session protection and user validation remain unfinished.
The [roadmap](roadmap.md), [evaluation](evaluation.md) and [security policy](../SECURITY.md)
describe the remaining work and evidence limits.
