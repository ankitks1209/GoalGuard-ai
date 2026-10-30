# ADR 0004: Local owner interface

Date: 2026-10-21. Status: ACCEPTED — initial three-screen frontend and sessions implemented. Deterministic handler/TCP/component checks and compact-browser synthetic inspection are recorded; broader browser acceptance and a combined provider flow remain pending.

## Context

Real model shopping and initial plan drafting now have separate observed results.
The next roadmap milestone is the three-screen owner interface. The specification
leaves frontend and browser-session choices open; the existing bearer-token API
is a development interface, not a browser authentication design.

## Accepted frontend decision

- Keep one Python backend and SQLite database. Prefer a React + TypeScript
  frontend built with Vite, served as static assets from the same origin.
  The human approved this frontend dependency/build/test toolchain on 21 October.
  Installation was authorized, and the owner subsequently generated the lockfile
  and ran the scaffold quality checks successfully in their normal Terminal.
  It does not put financial authority in the browser.
- Build exactly three screens: plan setup, exact-cart purchase review, and timeline.
  Owner unlocking is an inline state, not a fourth dashboard.

## Accepted local browser session

- Exchange the existing local owner token for an opaque browser session. Keep
  session state in server memory, expire it after 30 minutes, support logout and
  invalidate it on server restart. Never store the owner token in URLs/localStorage.
- The cookie contains a random session identifier, never the existing owner
  token. Expiry locks the owner interface and requires unlocking again; it does
  not cancel purchases, release reservations or discard payment-operation records.
  Existing ledger expiry and reconciliation rules still apply independently.
  Preserve non-secret in-memory form input when requesting another unlock;
  never persist the owner token with it or replay an interrupted mutation automatically.
- Use an HttpOnly, SameSite=Strict cookie; check session-bound CSRF tokens and
  expected Origin/Host on browser mutations. Keep development HTTP loopback-only;
  remote production deployment/HTTPS is a separate decision, not a claimed capability.
- Keep PayPal credentials/signing keys server-side and shopping-agent tools scoped.
  Every model proposal still needs exact-cart owner consent. Preserve original
  operation identities on retries; refreshing status never initiates a payment.
- Use synthetic AI draft inputs until the owner-data policy question is resolved.
  Financial equations, confirmation, reservations and payment rules stay in existing code.

## Accepted visual direction

Use a light, restrained finance dashboard with clear hierarchy, readable money
amounts and visible state labels. Detailed visual tokens and layout are implementation
choices within this direction, not new financial or payment behavior.

## Initial implementation notes

The owner-only overview supplies stored consent permits and the original payment
operation identity so an authenticated owner can resume deliberately after a
session change or page reload. This read does not issue consent; existing ledger
transitions still enforce the exact terms. Loaded purchase/permit data is cleared
when locking; only non-secret form input is retained in memory. No mutation is
automatically replayed. The built frontend is served on the Python API origin;
the separate Vite appearance preview does not proxy financial requests.

## Review of the earlier plain-JavaScript option

The earlier proposal prioritized avoiding dependencies. Plain HTML/CSS/JavaScript
remains viable for a tightly timeboxed demo, but editable bill collections, AI
preview/correction, concurrent purchase updates and payment-pending states make
shared UI state substantial even with only three screens. Engineering judgment:
React/TypeScript is the stronger fit for the intended maintained product if time
allows the frontend setup and tests. A framework does not establish visual quality
or security; design and behavioral checks still decide those outcomes.

Vite supports integration with an existing backend, so this does not require a
second deployed application server. TypeScript must have its own `tsc --noEmit`
check because Vite transpilation does not perform type checking. Add frontend
lint/type/test/build gates alongside the Python checks when the toolchain is installed.
Use npm and commit its generated lockfile once dependency resolution succeeds;
do not fabricate a lockfile or claim an uninstalled toolchain has passed.

The current Python `http.server` transport is for local development. Public
hosting would require a separately approved production HTTP/session/deployment
plan; the local cookie proposal is not a production-readiness claim.

Sources checked 2026-10-21:
[React UI states](https://react.dev/learn/reacting-to-input-with-state),
[Vite/backend integration](https://vite.dev/guide/backend-integration),
[Vite TypeScript](https://vite.dev/guide/features#typescript),
[Python HTTP server scope](https://docs.python.org/3/library/http.server.html).

## Acceptance before implementation can be considered complete

Write failing tests for missing/expired sessions, logout, wrong origin/CSRF,
agent-to-owner privilege attempts, exact-cart consent and safe status refresh.
Exercise the approved screens with keyboard navigation and their loading/empty/
error/pending states. Run all existing quality gates. A proposed design does not
establish security, rendered UI quality, or the combined sandbox flow.

## Human decision

Frontend direction and its toolchain are approved. In the follow-up the human
asked the builder to select the session approach that best fits the existing
product and explicitly selected the light, restrained dashboard. Adopt the
proposed local session with the continuity requirements above. Session expiry
cannot guarantee uninterrupted access; unlocking again is required. Durable
financial state remains independent of browser authentication.

The human also agreed that messy-input and repeated real-model evidence can be
added in a later reliability milestone. This does not establish reliability now
or authorize sending private household records to a model.
