# Owner form verification

Observed 28 October 2026 against the uncommitted working tree. This completes
the local implementation/review of the first remaining owner-UI item, not the
combined live AI-to-PayPal demonstration or submission readiness.

## Implemented scope

- Initial-plan AI drafting from a displayed read-only synthetic sample, explicit
  processing consent, Google free-tier data-use notice, loading, clarification,
  malformed/provider failure and manual fallback. Existing records and manual
  form values are excluded. Exact amounts/dates/obligations are visible before
  separate plan confirmation. Editing or requesting another draft invalidates
  the old preview; manual and AI preview requests cannot overlap.
- Existing cash-event API exposed for all six documented kinds, with positive
  integer cents, linked choices, exact review and external-activity confirmation.
  An unknown result freezes terms/ID, requires a manual audit read and offers
  only deliberate same-ID retry. Known validation failures retain editable input.
  Locking retains non-secret form state, clears consent and never replays a write.
- Timeline shows financial activity/amount/reference/record ID while retaining
  the selected ledger rows, server ordering and timestamp behavior.

## Evidence

| Gate | Actual result |
| --- | --- |
| Loopback probe before resumed baseline | Pass outside sandbox; sandbox listeners denied |
| Baseline | Python 227/227, 9 real TCP; frontend 29/29 before implementation |
| Python lint / types | Ruff exit 0; mypy exit 0, 25 source files |
| Complete Python suite | 227/227, 9 TCP, zero failures/errors/skips; evidence validator exit 0 |
| Branch-aware Python coverage | 85.30%; threshold passed |
| Frontend final gate | 52/52; code lint, token guard, types and build exit 0 |
| Frontend coverage | 96.31% statements, 92.63% branches, 99.09% functions, 98.66% lines |
| Browser comparisons | 149/149 launchable Chromium/WebKit cases; zero skipped/unexpected/flaky; updates disabled |
| Screenshot references | 72 comparisons; 15 new, 6 intentionally changed Budget/empty, 51 existing byte-identical |
| Source/wheel build | Exit 0 |
| Commit hooks | All three passed after activating the documented virtual environment |

The first hook invocation failed because child commands could not find `python`;
the activated-environment rerun passed. The first broader browser run was stopped
to correct a discovered API mismatch and does not count as the final pass.

Observed red → green evidence includes initially missing controls, an old AI
preview surviving a replacement request, absent financial audit details, the
actual API's nullable blocker contract, revision request mode after activation,
and overlapping manual/AI previews. Existing mocked preview fixtures incorrectly
used lists; they now follow the backend's `activation_blocked_by: string | null`.
The backend contract/ledger/payment code was not changed.

## Actual local HTTP walkthrough

The built UI used the real Python handler, owner session, CSRF protection and
SQLite ledger with **fixed simulated extraction**. No API responses were
intercepted in this walkthrough. One sample draft request did not activate a
plan; a separate fixture-owner confirmation did. Recording a $40 bill payment
and $25.50 savings deposit produced:

- Cash $534.50; unpaid bill $60; saved balance $325.50.
- Remaining contribution $74.50; available cash $350; captured spend $0.
- Two financial audit records; zero external browser requests, real model calls
  or PayPal calls.

See [sanitized evidence](../reports/owner-ui-demo.json). This proves local UI/API
wiring and deterministic accounting under synthetic conditions. It does not
prove real AI extraction or a provider payment. The disposable server was stopped
and its temporary ledger discarded after inspection.

Private logs use `.local/checks/owner-plan-ui-*`; final browser artifacts are
preserved in `owner-plan-ui-browser-evidence`. Generated environment/credential
files and raw records stay private. No dependencies, runtime financial rules,
payment authority, public deployment, commits or pushes were introduced.

## Visual review and limits

Viewed actual desktop/phone plan confirmation, bill-record review and financial
Timeline screenshots, plus expanded AI controls at desktop/320px and financial
controls on phones. Selected Instrument Sans, monochrome palette, flat rules,
native disclosures and existing spacing tokens are retained. The first form
remains essentials-first; optional features stay collapsed. A cramped AI notice
was given the existing 16px gap. IDs wrap on narrow screens. Fixed sample text
scrolls within its read-only field on small screens; review it fully before
consent. No new generic cards, gradients or motion were added.

Automated review includes axe, keyboard, overflow/reflow, enlarged text and the
previous session/payment regressions. This is not WCAG certification. Firefox's
10 configured cases remain blocked by its local launch failure; the default
159-case matrix is not claimed fully green. Manual screen-reader/native zoom,
genuine Linux references and hosted CI remain unverified.

Pending financial-record terms/IDs survive locking only in memory. After reload,
inspect Timeline before recording the activity again. Real owner text is outside
the AI demo scope. A fresh browser-to-model run and combined AI → owner consent
→ PayPal sandbox demonstration still require separate scoped verification.
