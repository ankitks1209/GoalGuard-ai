# Browser CI repair — 1 November 2026

The initial hosted run on checkpoint `e82c54e` passed both Python jobs and the
frontend job, but its browser job reported 86 passed and 73 failed cases. These
were real failures, not a green cross-browser gate.

## Corrections

- Pin the browser environment to Ubuntu 24.04, the OS used by the initial run.
  Keep the locked browser tools, zero-pixel comparison tolerance, no retries and
  snapshot updates disabled in the normal job.
- Capture missing Linux reference candidates in a separate deliberate workflow
  dispatch. Review images before adding them; never rename macOS references,
  commit from CI automatically or turn comparisons into automatic updates.
- Use native Shift+Tab to return from a screen to header navigation. The Firefox
  trace showed 80 forward Tab presses stopping at the last disclosure rather
  than wrapping through browser chrome. Keyboard reachability remains required.
- Retain full-control visibility checks with a bounded wait for native scrolling.
  Linux WebKit still clipped the current-cash field after that wait, reproducing
  a real visibility defect. The app now checks the focused control after native
  scrolling and reveals a clipped control instantly. It leaves visible controls
  alone and ignores a callback after focus has moved. It does not change focus,
  field values, financial state or payment authority.
- Select the intended status message within its feature. Pending refresh and
  completion live regions can briefly coexist; choosing the first match would
  hide ambiguity. Tests retain exact completion text and request-count assertions.

A focused component regression failed on the missing focus correction before
implementation, then passed with the visible-control and moved-focus cases.
The earlier post-reference run (`28532e2`) reported 153 passed and 6 failed cases;
its remaining visibility and live-region failures were retained and corrected,
not relabeled as success.

## Linux reference provenance and visual review

All 72 new Linux PNGs came from the actual Ubuntu capture in
[run 41239958811](https://github.com/ankitks1209/GoalGuard-ai/actions/runs/41239958811)
at `f19f48d`, whose runtime interface matches the preceding checkpoint. The
capture produced all images, then three post-capture status assertions failed:
69 cases passed and 3 failed. That capture was not a successful verification run.
The corrected normal comparison run is the acceptance gate.

Viewed all 72 candidates across desktop 1440px, phone 375px and narrow 320px,
using full images and grouped viewport review sheets. Instrument Sans, the
selected light monochrome tokens, flat rules, split desktop layout and stacked
mobile layout remain intact. Text, notices, amounts, consent controls and long
references wrap without crossing neighboring content. Empty history remains
distinct from unread history, and uncertain payment views retain their commitment
message. Some accessibility captures include the focused skip link at the capture
viewport; these are focus-state images, not the default screen.

All 72 existing macOS references were preserved byte-for-byte. Private review
artifacts and raw traces remain local. The candidate job records environment,
revision and hashes even when an assertion fails; its initial metadata step did
not run after the three failures, so no manifest from that first run is claimed.

## Verification

Local checks: Python 227/227, 9 actual TCP checks, zero failures/errors/skips,
strict report validation and 85.30% branch-aware coverage; Ruff and mypy passed.
Frontend 55/55, lint/token guard, types, coverage and build passed. Source/wheel
builds and actual commit hooks passed. The focused real-browser keyboard path
passed in Chromium and macOS WebKit.

All four normal hosted jobs passed in
[run 41290178880](https://github.com/ankitks1209/GoalGuard-ai/actions/runs/41290178880)
at `133b0e4`: Python 3.11, Python 3.14, Frontend Node 24 and Browser accessibility
and visual regression. The browser job passed 159/159, including Firefox and
WebKit, with all 72 Linux screenshot comparisons and updates disabled. The manual
candidate job is intentionally skipped outside a manual dispatch. The actual comparison job, rather than the reference
capture or local subset, establishes the hosted result. Current results are
available in [PR #1 checks](https://github.com/ankitks1209/GoalGuard-ai/pull/1/checks).

After the app correction, the local launchable matrix passed 149/149 with updates
disabled, and all macOS and reviewed Linux reference hashes remained unchanged.
Viewed the current desktop/phone WebKit plan-review renders: hierarchy, spacing,
field boundaries, wrapped obligations and the confirmation focus ring retain the
selected design. No palette, typography, layout or decorative motion changed.

Manual screen-reader use and native browser zoom remain unverified. Automated
checks do not establish WCAG conformance, live AI behavior or PayPal integration.
No model/payment provider was called during this repair.
