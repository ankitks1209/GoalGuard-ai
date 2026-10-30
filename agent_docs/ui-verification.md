# Owner UI verification

Status: local review completed for launchable engines on 26 October 2026; Firefox,
manual assistive-technology checks and Linux/hosted CI remain open. The three
selected screen layouts are implemented. Local results below do not establish
WCAG conformance or live payment integration.

| Area | Evidence and limits |
| --- | --- |
| Existing screens/states | Chromium at1440,375 and320px;57 screenshot references. |
| Responsive review | Chromium at768,801 and1024px; three screens, plan review, cart consent and uncertain-payment controls. |
| Reflow |320×256 CSS viewport models the layout available at400% zoom on a1280px viewport. Native browser zoom is not verified by this test. |
| Larger text |200% root-font preference at1280px; body computes to32px. This is not native browser zoom or a claim that every display font doubles. |
| Keyboard | Skip link, form/disclosures, preview, confirmation focus without confirming, exact-cart consent without approving, Timeline refresh. Focused controls must fit the viewport. |
| WebKit | Desktop1024px/phone375px. macOS full traversal uses Option+Tab, as verified with an isolated preflight. This is not a manual Safari application review. |
| Firefox | Downloaded engine cannot launch: “Could not find profile folder”, including a dedicated workspace profile. Checks remain configured and are blocked locally, not passed. |
| Automated accessibility | axe WCAG2A/AA,2.1AA and2.2AA tags, document overflow and navigation overlap geometry. |
| Manual assistive technology | Screen-reader narration and native400% zoom remain unverified. |
| Linux/hosted CI | Linux references have not been generated or reviewed. No Docker/Podman available locally; no reviewed commit/push or hosted run performed. |

Final launchable subset:137 passed,0 failed/skipped/flaky, including all57 existing
screenshot comparisons with updates disabled. Firefox's10 cases are blocked before
page execution and are not counted as passes. The default matrix contains147 cases.
Python227/227 (9 real TCP,0 skips), frontend29/29, lint/type checks, builds and
all3 commit hooks passed. Backend branch-aware coverage85.30%; frontend
statements96.55%, branches89.14%, functions98.63%, lines97.77%. Wheel-resource
hash comparison and an installed-wheel smoke outside the checkout passed.

The default browser command includes Firefox. An explicitly selected launchable
subset cannot be described as a fully green cross-browser gate. Keep failures and
omissions visible; never rename macOS references as Linux references.

## Findings and corrections

Visual inspection found enlarged navigation labels overlapping neighboring icons,
despite passing axe and document-overflow checks. A focused geometry regression
failed on the overlap before the CSS fix. Allowing navigation items to wrap then
passed all five enlarged-text cases. This follows the selected navigation style
and adds no new colors, spacing values, motion or financial behavior.

The first WebKit keyboard check expected macOS Tab to visit links. A minimal
preflight showed Tab visiting fields and Option+Tab visiting links/buttons. The
test now uses the native full traversal sequence on macOS; focus and viewport
assertions remain unchanged. No OS preferences or security protections changed.

Firefox failed with both ordinary temporary profiles and an explicit synthetic
workspace profile. A [reported Playwright/macOS launch issue](https://github.com/microsoft/playwright/issues/42768)
has similar symptoms; that is a diagnostic lead, not confirmation of this host's
root cause. No user Firefox profile was read and no broader permissions granted.
Preflight a failing engine once before repeating a full matrix.

The package declaration now includes the resource namespace. The wheel's two
resource files retain their previous hashes. An isolated environment outside the
checkout imports the drafting module/resources and runs CLI help/deterministic
demo. CI includes a corresponding installed-resource smoke check. No runtime
dependency or model/payment call was added.

## Remaining hands-on checks

1. At native400% browser zoom, traverse all three screens and expanded plan
   sections; verify no content/control loss or obstructed focus.
2. With a screen reader, review headings/landmarks, field labels and helper text,
   disclosure state, validation announcements, exact preview totals and consent.
3. Review Firefox in a working environment and Safari itself on target hardware.
4. Generate Linux screenshot candidates in Linux, inspect every change, then run
   hosted checks against a reviewed revision. Publishing requires separate approval.

Use disposable synthetic data for these checks. Plan confirmation, cart approval
and provider actions are not required for the visual/keyboard review.
