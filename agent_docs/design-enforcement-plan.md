# Design enforcement setup — approved 23 October 2026

The selected design remains a static review until the owner says **design locked**.
The original design brief explicitly requests a token guard, accessibility CI and
visual regression setup. The owner explicitly approved the two development packages and Chromium download.
The setup is installed. The first budget-screen migration resolves the formerly
observed token/contrast violations; older setup results below are historical.

## Approved development dependencies

Installed from the registry and exact-pinned in package.json/package-lock.json:

- `@playwright/test` 1.64.1: deterministic Chromium browser tests and screenshot comparisons.
- `@axe-core/playwright` 4.14.0: automated accessibility checks inside that browser runner.

No backend or browser-app runtime dependencies changed. Playwright Chromium1248
and its headless shell were installed after approval; npm reported zero vulnerabilities.
No production deployment occurred.

## Concrete integration

| File or command | Intended check |
| --- | --- |
| `scripts/check_design_tokens.py` | Dependency-free guard over production CSS and component style literals; only `src/styles/tokens.css` may define raw colors, dimensional spacing, radii and responsive thresholds. Check JSX inline style objects and SVG color/stroke literals too. Allow documented semantic CSS keywords and unitless zero, not arbitrary numeric escape hatches. |
| Guard fixture tests | Prove raw hex/RGB/named colors, dimensional spacing and inline style literals fail; variable-based values pass. Preserve line/file diagnostics. |
| `frontend/playwright.config.ts` | Node 24; isolated loopback Vite server; deterministic Chromium viewport matrix; private local output directory and runner-temp CI reports; no reuse of an unrelated live server. |
| `frontend/tests/browser/fixtures.ts` | Synthetic plan/cart/timeline and owner-session responses; intercept app API routes; block unexpected network/provider destinations. No real owner key, financial records, model or PayPal configuration. |
| `frontend/tests/browser/accessibility.spec.ts` | Axe checks for setup, review and timeline; keyboard order/focus; relevant loading/empty/error/offline/expiry/uncertainty states; mobile reflow and text enlargement. Automated checks supplement manual review and cannot certify WCAG conformance. |
| `frontend/tests/browser/visual.spec.ts` | Screenshot comparisons for selected desktop/mobile screens and important states; wait for fonts; stabilize synthetic time/data; no arbitrary animation delays. Store approved synthetic image baselines; never automatically bless future changes. |
| `npm --prefix frontend run check:tokens` | Token rule is part of lint/commit/CI gates. Existing legacy app CSS currently has raw values; do not quietly exempt it. |
| `npm --prefix frontend run test:browser` | Browser accessibility plus screenshot tests. Initial snapshot creation requires reviewing the actual images, not a fabricated pass. |
| `.github/workflows/checks.yml` | Keep Python 3.11/3.14 and Frontend Node 24 jobs; add Chromium install and browser checks. Upload only explicit synthetic runner-temp artifacts, never `.local/` wholesale. |
| `AGENTS.md` | Owner's exact mobile/desktop visual-review rule added. |

The token CSS is a requested design artifact at the repository-root path
`src/styles/tokens.css`. It is not imported by the current frontend. Its future
frontend import and Vite file-access scope need to be limited to this stylesheet
directory, not private project material. This requires no financial API changes.

## Execution and remaining migration

1. Verify loopback binding and the complete existing baseline before application work.
2. Add the approved development packages with `--save-dev --save-exact`; retain lockfile.
3. Observe a focused failing guard fixture, implement the minimum guard, then run
   its positive/negative cases. Do not claim retroactive TDD.
4. Prepare isolated fixtures/browser configuration and actual accessibility/screenshots.
5. Keep existing baseline/coverage thresholds intact. Report any legacy UI failures;
   do not hide them with exclusions. UI migration still requires the explicit lock.
6. Run lint, types, full deterministic tests, coverage, builds and relevant hooks.
   Report installed/setup/verified/blocked separately. Hosted CI remains unverified
   until it actually runs remotely. No commit or push is authorized.

## Historical setup results before UI migration

- Existing baseline passed before tooling changes:222 backend cases,9 TCP;24 frontend tests.
- Token guard: observed missing-module red, then five focused tests passed. Guard
  exits1 on164 existing stylesheet violations; no exemptions were added.
- Browser axe setup initially stalled because the test clock paused browser timers.
  Freezing Date alone repaired the harness. It now reports actual legacy text
  contrast failures (examples3.72:1 and2.91:1 where4.5:1 is required).
- Application component/styles changes remain blocked on the explicit design lock.
- Hosted CI/Linux screenshots and complete manual accessibility are unverified.

- Final local browser matrix:57 checks;30 passed,27 failed,0 skipped/flaky.
  All27 axe cases reported color-contrast failures in the legacy UI;27 local
  screenshot comparisons and3 keyboard/expiry checks passed. Full axe JSON is
  attached in the private browser report. Screenshots were inspected in three
  contact sheets and the320px cart at full size. These are legacy reference
  captures, not approval of the old visual identity.
- Python lint/types/227 cases (9 TCP)/85.30% coverage/build passed (exit0).
  Frontend code lint/types/24 tests/build passed separately (exit0). Full frontend
  check/hooks exit1 because token lint correctly rejects164 legacy literals.
  Python hooks pass with the virtual environment activated. Build produced wheel
  and sdist, with an existing setuptools resources-package configuration warning.
- Proposed narrow rule after repeated legacy failures: inventory each source/rule
  once, retain its evidence, then rerun after the relevant migration; never keep
  retrying unchanged UI or suppress rules. This is a process proposal, not a
  waiver of the required final gates.

## First-screen migration

Canonical tokens are imported, and the selected font/license is served locally.
The token guard now reports zero violations. Budget presentation and shared
controls are migrated; no financial/payment/session authority was moved. Browser
checks also verify that the Vite token import cannot expose a synthetic private
file. Local updated PNGs were reviewed; screenshot comparisons never update
baselines in CI. Linux baselines/hosted CI still require actual platform evidence.
See design-review.md for the first-screen critique and manual limitations.
