# GoalGuard product specification

Status: agreed MVP direction; this file specifies behavior, not a claim of completion.
Implementation/evidence status lives in [roadmap](roadmap.md) and [evaluation](evaluation.md).
The human owns product and architectural decisions; unspecified behavior requires a question.

## Users and purpose

Primary: individual/household owners delegating shopping while protecting bills,
a cash buffer and a savings target. Secondary: developers connecting scoped agents.
GoalGuard helps avoid conflicting purchases against the same finite cash allocation.
It does not hold savings or provide investment recommendations.

## Core flows and acceptance criteria

| ID | Flow | Acceptance criteria |
| --- | --- | --- |
| PLAN-1 | Owner creates a plan | Manual input accepts bounded integer USD cents, timezone, current cash, bills, buffer, expected income and an optional savings goal. Reject invalid/missing required fields without activating purchasing. |
| PLAN-2 | Owner requests an AI draft | Explicit permission precedes model processing. The browser demo accepts only displayed built-in synthetic sample text; manual entries and existing financial records are excluded. Extract a validated initial draft; show clarification/manual fallback; review every amount/date/bill and separately confirm the exact preview. Do not activate automatically or invent financial facts. |
| PLAN-3 | Preview and confirm | Code computes the savings contribution and cash protection. Owner reviews/explicitly confirms the preview. Changed/stale previews cannot silently activate. Infeasible/waiting plans block purchases; zero capacity requires confirmation. |
| BUY-1 | Agent proposes | Agent selects catalog SKUs/quantities; server supplies merchant and delivered total. Agent sees scoped purchase results/denials, not bills, income, buffer, goals, owner consent or provider IDs. |
| BUY-2 | Shared allocation | Reserve atomically against actual available cash. Concurrent proposals cannot overallocate. Capture remains counted as spending. Same-key identical retries reuse one result; changed payloads are rejected. |
| BUY-3 | Denial recovery | Return a structured denial and at most one feasible catalog alternative. Agent checks original requirements and revises at most once. Eight tool calls per run; three distinct proposals per agent/plan period. New runs do not reset quotas. |
| CONSENT-1 | Owner reviews a cart | Bind consent to the exact cart, amount and expiry. An agent cannot approve itself. Price/cart changes invalidate the pending consent. Internal reservation expires after 15 minutes, including exactly at deadline. |
| PAY-1 | Buyer approves on PayPal | Create a sandbox AUTHORIZE order. Verify provider order status and exact terms before authorization; a browser redirect alone is not evidence of approval. |
| PAY-2 | Capture, void or reconcile | Persist an operation before provider I/O. Capture no more than the approved total. Unknown results retain the commitment; refresh verified status using the original operation identity. Verified void releases capacity. |
| PLAN-4 | Update financial facts | Pair bill payments and savings deposits with cash/protection changes atomically. Financial revisions release pre-payment reservations; verified authorizations retain original terms. Block revisions during in-flight/uncertain payment calls. |
| PLAN-5 | Rollover and refund | Require next-period confirmation; carry cash and outstanding obligations once. Owner records actual received refunds as linked inflows with captured amount limits. |
| UI-1 | Owner experience | Three screens: plan setup, exact-cart purchase approval, timeline. After a successful exact-plan confirmation and refreshed budget read, show the budget directly, collapse setup and offer explicit editing. Keep recovery visible if the read fails. Each relevant screen has loading, empty, validation, denial, failure and pending states. Owner sessions/request protection precede browser payment actions. |
| UI-2 | Local owner session | Exchange the existing owner token for an opaque server-memory session lasting 30 minutes, with logout and restart invalidation. The HttpOnly, SameSite=Strict cookie contains only a session identifier. Browser changes require session-bound CSRF and expected Origin/Host checks. Expiry requires unlocking again without releasing ledger commitments; retain non-secret in-memory form input and never automatically replay a mutation. |

## Owner interface decisions

React + TypeScript + Vite over the existing backend and frontend quality tooling
are approved. The human selected a light, restrained finance dashboard and
delegated session selection; adopt the local session in UI-2. See
[ADR 0004](../agent_docs/decisions/0004-owner-interface-proposal.md).
These are agreed requirements; current implementation and verification scope is
tracked in [roadmap](roadmap.md).

## Financial contract and edge cases

The precise equations, date boundaries and revision classifications are maintained
in [financial-semantics.md](financial-semantics.md); do not duplicate or simplify them in prompts.

- Protect overdue bills and bills through the later of month end and next payday,
  including payday itself. Expected income never authorizes spending.
- Use the confirmed timezone; the initial partial month counts as a full contribution period.
- Missing/stale/overdue income information blocks new purchases.
- External corrections can expose a deficit; retain existing payment obligations.
- Approval at expiry fails. Once payment I/O starts, local expiry cannot release money.
- Duplicate events, simultaneous reservations, retry races, price changes, prompt
  injection and process crashes must preserve the same authority and accounting rules.
- Counteroffers must satisfy the owner's requirements; outcome-based financial
  inference remains a disclosed limitation despite quotas and limited responses.
- The catalog is synthetic and fulfilment is manually simulated. Label both in demonstrations.

## Out of scope

Live-money use, investment advice/returns, automatic savings transfers, bank
aggregation, broad real-retailer checkout, autonomous model consent/payment authority,
production deployment guarantees and horizontally scaled multi-household operation.
A separately verified immediate-capture fallback would require explicit scope/evidence
updates; it cannot count as a passed authorize/capture gate.

## Quality and evidence acceptance

- New behavior follows observed red → green → refactor; human review retains final ownership.
- CI requires lint, typecheck, complete deterministic tests with no skips/eight existing
  TCP checks, at least 80% aggregate branch-aware coverage, and a successful build.
- Include all runtime modules in coverage, even previously untested model/CLI modules.
  Coverage is a floor, not proof of financial correctness.
- Separate synthetic callers, fixture replay, actual sandbox results and real-model runs.
- Do not claim full integration from separate component demonstrations. A judging build
  still needs a combined AI → owner consent → sandbox flow and a runnable setup.

## OPEN QUESTION

- Owner chose synthetic/sample text only for the browser demo on 27 October.
  Actual private records remain excluded from model processing. Any future
  real-record drafting exception requires a separate explicit decision; consent
  to the built-in sample does not grant that exception.
- Repeated baseline/ablation scenario matrix, repetitions and pass thresholds need confirmation.
- A second model/vendor and any sponsor integration remain undecided; do not add paid fallback.
- Minimum per-module/critical-branch coverage beyond the 80% aggregate floor is undecided.
- Public hosting, demo credentials and retention rules need decisions before deployment.
