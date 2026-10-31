# Synthetic browser checks

Run `npm --prefix frontend run test:browser` after installing the locked dev
dependencies and `npx playwright install chromium` inside frontend. The server
uses an exclusive loopback port 5189. Fixtures block external HTTP destinations
and every unimplemented API/mutation; no live credentials/providers are used.
Dates, locale, timezone and clock are fixed. Desktop 1440px, phone 375px and
narrow 320px Chromium projects exercise the same existing application.

`test:a11y` runs axe plus keyboard, expiry and reflow checks. It does not certify
WCAG conformance. Loading/empty/error/offline/locked/uncertain fixtures cover
workspace states; screen-reader use, zoom, dialogs and every action state still
need manual review. Failures in the legacy UI must be fixed during the approved
design migration, never suppressed to make this setup green.

`test:visual` compares screenshots. Initial local legacy captures are engineering
reference images, not approval of the old design. Snapshot names include OS so
different font rasterizers are not silently treated as equivalent. Linux CI
baselines must be captured and visually reviewed on Linux before that job can
pass. A missing baseline is a failure. CI never writes approved snapshots.

The browser job uses Ubuntu 24.04. A deliberate `Checks` workflow dispatch also
runs a separate Linux-candidate job: it captures missing references only and
uploads the synthetic PNGs, source revision, environment and SHA-256 manifest.
Review those images against the design system before adding them to Git; the
job never commits them or changes the normal comparison gate. Existing references
are never replaced by that capture command.

For an intentional UI change, inspect the failed expected/actual/diff images,
compare mobile and desktop against agent_docs/design-system.md, then explicitly
update only the affected images with Playwright's `--update-snapshots` option.
Review the resulting PNGs and Git diff. Never blanket-update to hide failures.
Keep approved synthetic PNGs beside the tests. Local reports/traces remain under
`.local/checks/browser`; CI uploads only its synthetic runner-temp directory.

The dependency-free token guard runs in `npm run lint` and therefore existing
commit/CI gates. It scans CSS literals (including media thresholds), literal JSX
style objects and SVG presentation colors/strokes. It intentionally does not
interpret computed JS styles or SVG path geometry; code review must reject
computed styling that evades canonical tokens. Financial numbers are not styles.
