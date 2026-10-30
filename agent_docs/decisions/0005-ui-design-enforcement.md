# 0005 — Collaborative UI system and synthetic browser enforcement

Status: approved for first-screen implementation (23 October 2026).
Owner replied “proceed” to the final lock request; this authorizes the reviewed
UI system without requiring a literal phrase. Pause after the first budget screen.

The owner selected a light Teenage Engineering/Enpower blend, Instrument Sans,
split workspace, hierarchical control radii and no transitions. The detailed
choices and rejected alternatives live in design-system.md. Financial, session
and payment behavior remain governed by the existing contracts.

The owner explicitly approved @playwright/test, @axe-core/playwright and Chromium
as development tooling. Use synthetic intercepted API responses and an exclusive
loopback Vite server; block unexpected external requests and mutations. Keep the
Python matrix and existing coverage thresholds. Add a canonical-token source
guard, automated accessibility checks and reviewed screenshot baselines.

New checks may expose existing UI failures before the redesign. Report them;
do not exempt legacy styles or suppress accessibility rules. The owner must say
“design locked” before application styling changes, and review the first real
screen before further screens. Browser automation supplements human review and
does not prove WCAG conformance or live provider integration.
