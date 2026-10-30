# Architecture guardrails

The approved shape is one Python backend, one SQLite database and a thin owner
interface. React + TypeScript + Vite is approved for that interface, using
same-origin built assets and a separate frontend quality toolchain; see
[ADR 0004](decisions/0004-owner-interface-proposal.md). The Python backend keeps
the current pip/setuptools stack. The implementation map and
lifecycle are in [docs/architecture.md](../docs/architecture.md); financial equations
are in [financial-semantics.md](../docs/financial-semantics.md).

## Authority boundaries

- Models select/explain; owners confirm plans and exact carts; trusted gateway code enforces.
- SQLite writers acquire `BEGIN IMMEDIATE` before allocation. Keep provider I/O
  outside the transaction, after persisting the payment operation/request ID.
- Internal allocation and PayPal authorization are separate. Captured spending
  stays deducted. Unknown provider outcomes remain committed until reconciled.
- Shopping tools use scoped tokens and allowlisted data. Owner plan drafting is
  a separate, explicitly consented processing path; it cannot activate a plan.
- Model output, product text and return URL parameters are untrusted inputs.
- Existing loopback bearer tokens remain development API credentials. The approved
  owner-browser backend exchanges the owner token for a temporary session ID;
  cookie/CSRF/origin protection has deterministic handler/TCP evidence. The initial
  frontend is integrated on the API origin and inspected using a disposable
  synthetic household. Session expiry, logout and restart invalidation do not
  touch the financial ledger. Form input remains in memory; mutations never replay.
- The private owner overview projects household purchases, existing consent permits,
  latest operation IDs and audit events after an owner-only role check. Reads do
  not issue consent. Existing ledger/payment transitions still enforce every action.

## Changes

Consult [spec](../docs/spec.md) before changing behavior. A new framework, external
service, database or dependency requires the human's decision. Record accepted
trade-offs in a numbered ADR with context, decision, consequences and verification.
Preserve legacy local-only material; do not promote it into public documentation.
