# GoalGuard — pre-lock review

## Latest review — responsive and accessibility follow-up, 26 October 2026

Expanded review to768/801/1024px, short-height320px reflow,200% root-font preference
and WebKit desktop/phone. Visual inspection caught overlapping navigation labels
at enlarged text even though axe/document-overflow checks passed. An observed
failing geometry check preceded the CSS wrapping correction. Viewed corrected
enlarged-text,801px, tablet and WebKit phone/plan-preview renders: labels are
distinct, focus remains visible, forms wrap, and the selected type/colors/flat
rules remain. The actual app behavior/financial controls did not change.

Final launchable subset137/137 passed, including57 unchanged screenshot references;
Firefox10 cases remain host-launch blocked and configured. Default147-case browser
gate is not claimed fully green. Python227/9TCP, frontend29, coverage, lint/types,
builds and all hooks passed. The package-resource declaration warning is removed;
wheel resource hashes/imports and isolated installed CLI/demo smoke passed.
No npm dependency, new style token, security preference or permission change.

Native400% browser zoom, screen-reader narration, Safari itself, Linux references/
hosted CI and live provider integration remain unverified. Read the
[verification report](ui-verification.md) for scope and exact remaining checks.

## Latest review — selected Timeline A implemented, 24 October 2026

Owner selected A—ledger rows. The app now has one heading, timestamps in a narrow
desktop column and event/reference text in the wider column, separated by thin
rules. The canonical timeline column token uses the selected1:3 proportions and
stacks at800px. Existing event names, server order (including equal-time records),
local timestamp formatting and purchase/financial-plan references are retained.
No filtering, regrouping, payment controls, backend or dependency changes.

Observed a focused failing test: unread/failed Timeline data displayed “A fresh
start”. Nullable history and explicit loading/unavailable states corrected it;
the test then passed through deliberate refresh recovery with no POST. Empty
copy appears only after a successful read of an empty array. Existing session,
consent and payment behavior remains covered by the unchanged regression suite.

Viewed actual ready, four-event history, loading, empty, error and offline renders
at1440/375/320px. The selected type, spacing and neutral palette remain; no new
shadows, accents, card grid or motion. Long references wrap within their column.
The keyboard refresh focus ring is visible. Phone rows take more height than a
compact table but preserve every event/reference in reading order. Event labels
retain backend wording. Three existing Timeline references changed; the other39
existing screenshots were byte-identical. Added and inspected15 state/history
references. The42-case generation run passed all behavior/accessibility checks.

Python227 cases/9 real TCP/0 skips, validator0, branch-aware coverage85.30%; frontend
29 cases with96.55% statements/89.14% branches/98.63% functions/97.77% lines.
Ruff/mypy24files, token guard, frontend types/lint, both builds and all3 hooks
exit0. Existing resources-package build warning remains. Final browser run passed
102/102 with0 failed/skipped/flaky and all57 screenshot comparisons passing;
reference updates were disabled. These are local synthetic checks.
Read-only HTTP verification confirmed the synthetic preview on8766 serves the
current built index; app browser open was requested (queued). Rendered evidence
comes from the isolated browser runner; live app-tab state was not inspected.
Manual screen reader,400% zoom, other browsers, Linux screenshots/hosted CI and
complete browser-to-PayPal integration remain unverified. Owner review is next.

## Historical Timeline proposals, 23 October 2026

Owner accepted the implemented Purchase screen with “ok”. Current Timeline still
repeats its heading; its existing desktop/phone/narrow ready screenshots were
verified unchanged in3 comparisons. Prepared A ledger rows (recommended for
aligned dates and flat rules) and B vertical event trail. Both use the selected
type/palette/wordmark and preserve the same four synthetic event records/order.
B uses more desktop height but slightly less phone height in this specimen.
No rejected generic defaults, new actions or production code/token changes.

Inspected both actual renders at1280/375/320px. Font loading, no document overflow
and automated WCAG checks passed6/6 static preview cases. These are appearance
studies of ready data, not live history or app-integration evidence. Current full
local gates passed:227 Python cases/9 TCP/0 skips,85.30% coverage;28 frontend
cases, lint/types/builds/all3 hooks exit0. Existing packaging warning remains.
The complete87-case production browser suite was not rerun for static-only work;
its previous pass is historical. Manual screen reader/zoom, other browsers,
production Timeline non-ready states and hosted/Linux CI remain unverified here.
Owner choice is pending under the original one-step design-partner rule.

## Latest review — selected Purchase layout A implemented, 23 October 2026

Owner selected A. The app now has one Purchase heading, cart/items/charges on
the left and status/total/deadline/consent/actions on the right. At800px and below,
cart precedes decision. Stored cart details remain visible for closed requests.
Existing action conditions, exact-cart signature, payment requests and sessions
are retained. No new dependency, production token value or backend change.

Observed a focused failing test: unread/failed data incorrectly showed the empty
message. The correction shows loading or unavailable status and withholds a zero
count until a successful response. The focused test then passed, including manual
refresh recovery with no POST. Additional browser checks verify keyboard consent
per cart, changed-term invalidation, long labels/SKUs and restored payment controls.
These checks use synthetic data and block all mutations/external requests.

Viewed actual ready/uncertain/empty/loading/error/offline and five restored
payment states at1440,375 and320px. A follows the selected split composition,
Instrument Sans and thin rules with no new hues/shadows/motion. Phone SKU text
wraps within its column; long payment labels wrap without horizontal scrolling.
Critique: phones still require scrolling through the exact cart before consent;
this is the selected reading order, and no required cart terms were hidden.
Six existing Purchase screenshots changed; the other21 were byte-identical.
Added15 state references, inspected them, then passed all42 final comparisons.
The mutable-cart stress test exposed shared nested fixture data; fixture copies
now isolate cart items, keeping subsequent screenshot data consistent.

Final local checks:227 Python cases,9 real TCP,0 skips/failures/errors; validator0;
branch-aware coverage85.30%. Frontend28 cases; statements96.53%, branches88.92%,
functions98.61%, lines97.76%. Ruff, mypy24files, frontend lint/types/token guard,
both builds and all3 hooks exit0. Browser87/87,0 skipped/failed/flaky; reference
updates disabled in the final run. Existing resources-package build warning remains.
Synthetic preview restarted on8766; requested app browser open (queued). Current
interactive app-tab state was not inspected; rendering evidence comes from the
isolated browser runner. Manual screen reader/400% zoom, other browsers, Linux
references/hosted CI and live payment integration remain unverified.

Review the implemented Purchase screen with the owner before changing Timeline.

## Historical Purchase layout proposals, 23 October 2026

Owner authorized beginning this screen. Inspected the current synthetic Purchase
view: the heading repeats and cart details/consent have little visual separation.
Prepared two static alternatives using existing tokens/type/icons: A cart plus
decision in a desktop split (recommended), B a continuous receipt with consent
below. Phones stack in reading order. Both retain the chosen neutral theme and
flat rules; neither adds the rejected generic defaults. A uses desktop space more
efficiently; B favors linear scanning but requires more scrolling.

Viewed both at1280 and375px with loaded local font and no measured document
overflow. These previews demonstrate one synthetic reserved cart with disabled
buttons. They are not payment or app-integration evidence. No production code,
tokens, snapshots or financial/session behavior changed. Owner choice is pending.
All current local lint/type/test/coverage/build/hooks passed:227 Python cases,
9 TCP,0 skips,85.30% branch-aware coverage;27 frontend cases. Production browser
checks were not rerun for static proposals.320px, other browsers, screen readers,
400% zoom, Linux screenshots and hosted CI remain unverified for this work.

Earlier review sections below are historical and may describe superseded states.

Status: owner replied “proceed” to the final lock request on23 October2026.
The selected design is approved for the first budget screen; further screens wait
for review. Pre-lock observations below are historical evidence. Existing application behavior, sessions, ledger and payments stay intact.

| Area | Selected direction |
| --- | --- |
| Main job | Safely spendable money first, then purchase review |
| Identity | Merge Teenage Engineering technical structure/icons with Enpower large type and offset composition |
| Personality | Calm, clear, reassuring; not flashy, cold or preachy |
| Palette | Light blend: paper, charcoal ink, muted secondary text, thin neutral rules; dark primary action, no orange button |
| Typography | Instrument Sans, regular400/medium500; tabular money; large spendable figure |
| Layout | Split workspace: budget/facts left, requests right; budget then requests on phones |
| Spacing | 4/8/12/16/24/32/48/64px, shared edges, left alignment |
| Shape | Square content,4px fields,6px actions,8px dialogs;1px borders; shadow only on dialogs |
| Motion | No transitions, entrances, decorative scroll or blanket hover effects |
| Voice | Direct; action/object labels, recoverable errors, explanatory empty states |
| States | Loading/empty/error/offline for three screens; existing expiry, denied/invalid, pending and uncertain-payment cases |
| Accessibility | Standard16px body/44px action targets; WCAG2.2AA target, keyboard/focus/status semantics, mobile-first reflow |

## Generic-default review

- The light paper surface is paired with sans-serif typography and monochrome
  controls, without the cream/serif/terracotta combination.
- The spendable amount remains the main visual emphasis. Technical icons and
  navigation serve actual sections; no decorative numbering, repeated all-caps
  overlines, dot-separated metadata strings or arrows on every action.
- Use flat rows and thin rules, not a grid of identical rounded/shadowed cards.
  Small corner radii apply only by control hierarchy; elevation is dialog-only.
- No neon-accent dark theme, gradient washes, component-framework defaults or
  automatic entrance/scroll/hover effects.
- Large display type can become marketing decoration if it pushes controls too
  far down. The selected split layout brings requests beside the balance. Final
  form-heavy screens still need that critique during implementation.
- Semantic success/warning/error roles currently alias the approved ink, matching
  the reviewed monochrome state board. Explicit text carries the meaning; no
  new green/amber/red palette is silently introduced. This alias choice must be
  visible in the final review rather than presented as separate color approval.

## Artifacts and remaining work

- Canonical design tokens: `src/styles/tokens.css` (not imported by the app yet).
- Decision history and financial/session constraints: `agent_docs/design-system.md`.
- Reviewable tooling proposal: `agent_docs/design-enforcement-plan.md`.
- Owner approved Playwright/axe and Chromium; exact-pinned tools are installed.
- New token/axe gates expose existing UI literals/contrast failures. Migration must
  resolve them after lock; the complete new gate is not green.
- Combined prototype inspected at1280/375/320px. At320px navigation crowding was
  fixed in the static preview/tokens. Narrow child-frame overflow was not measured.
- Screenshot setup uses synthetic data; hosted Linux baselines remain unverified.
- Production keyboard/dialog, screen readers, zoom/reflow and complete contrast
  across all component states remain unverified. Sample checks are not WCAG certification.
- No new model/PayPal run, production deployment, commit or push is authorized.

Owner subsequently approved proceeding. Review the first implemented budget
screen with the owner before redesigning further screens.


## Actual pre-lock verification

Existing baseline was green before tools were added. The selected static design
was inspected at desktop/375/320px; body/nav/focus and contrasting text were
reviewed. The legacy application does not yet match it: serif headline, small
all-caps labels, sage panels and repeated rounded cards remain migration work.
Phone forms are long and the three equal metric panels delay purchase review;
the selected spendable-first split composition addresses that hierarchy.

New tooling is present and executing. All27 local screenshot comparisons and
three skip-link/expiry checks passed. All27 axe screen/state/viewport cases fail
on existing color contrast; token lint finds164 existing raw stylesheet values.
No rules were disabled. Existing Python227 cases/nineTCP and frontend24 unit
tests, code lint/types, coverage and builds pass separately. Full frontend
lint/check and combined hooks remain red until migration. CI/Linux screenshots,
manual screen readers, zoom, final dialogs and production-state accessibility
remain unverified. Review this plan and the monochrome status treatment before
saying **design locked**. Then implement and review the first screen only.


## First budget screen — awaiting owner review

The selected system is now applied to the budget screen and shared controls.
Safely spendable cash leads; cash/protection/commitments/captured spending remain
separate server-provided values. A read-only request summary opens the existing
purchase review without granting consent or executing payment. Existing plan
preview/confirmation, sessions, exact-cart consent and pending-payment code remain.
Purchase/timeline components retain their existing structure; only shared styling
and the common page heading have changed.

The old164 raw style findings were eliminated with canonical tokens. Shared
colors now meet the automated contrast checks. Instrument Sans is bundled locally
with its license, and Vite permits only frontend files plus the token directory;
a synthetic private-file request is verified forbidden. Loading ends after failed
reads, manual refresh clears stale errors, and forms are retained across sessions.
The new summary navigation and read-error recovery have observed failing tests
followed by passing regressions; visual-only styling uses rendered evidence.

Viewed the actual budget page at1280px and screenshots at1440/375/320px. The amount
is the sole large emphasis; navigation uses original line icons; content remains
flat and square, controls6px/fields4px, no orange/gradient/card shadows/transitions.
Body16px, visible focus and at least44px standalone targets. The narrow layout
stacks budget, requests and the existing form. No horizontal document overflow
in representative and large-amount/long-name cases. All27 updated screenshots were
inspected in desktop/phone/narrow contact sheets, with phone top at full size.

Critique: the retained manual plan form is long on phones. Do not invent collapsing
sections or a new editing flow before the owner reviews this screen. Purchase
review and timeline still need their own design pass after that review. Automated
checks do not verify screen-reader use,400% zoom, every browser or future dialogs.
Linux screenshot baselines and hosted CI remain unverified. No live provider
calls, commit or push occurred. Owner review is the next action.

Verification after the final recovery correction:227backend tests/nineTCP,26frontend
tests and63browser checks passed. Token lint has zero findings; lint/types/builds
and all commit hooks pass. Backend coverage85.30%; frontend statements97.27%,
branches89.01%. These are local synthetic/deterministic results; remote/platform
and manual limits above remain.


## Owner feedback applied — essentials first

Owner selected A after finding the form too demanding. Cash, buffer, next payday
and expected income remain visible; bills, savings and metadata expand on demand.
This reduces initially visible text/date inputs from14 to4 for the synthetic plan
with one bill and one savings goal. The actual required facts did not disappear:
name/timezone still require explicit entry, and invalid fields reveal their section.
Collapsed values remain in the preview; optional sections cannot erase protections.
The review states the plan name, timezone, bill count and goal inclusion.

Observed tests failed on the old expanded form. Native automatic invalid-field
reveal failed on three viewports; an explicit invalid-event reveal repaired it.
Keyboard opening/closing and preservation of existing terms pass focused checks.
Viewed updated ready/empty screenshots at1440/375/320: flat rules, selected type,
no new colors/shadows/motion. The phone page is shorter, though the budget overview
still precedes the editor. No wizard, AI drafting or backend change was added.

## Owner-selected connected wordmark — 23 October 2026

Owner selected C from the three original wordmark studies. The app now displays
`goalguard` on one line: regular `goal`, medium `guard`, with an ink underline
under `guard`. Existing type, spacing and stroke tokens supply every style value.
The accessible name remains “GoalGuard” and the link still targets main content.

Viewed the rendered budget screen at1440,375 and320px. The underline clears the
letters and navigation; the wordmark remains intact without overflow. Desktop
changes are confined to the wordmark bounds; phones also become shorter because
the stacked name is now one line. Reviewed all27 state snapshots in contact
sheets, then intentionally updated their shared header references. The selected
neutral palette, technical navigation and four initial form fields remain. No
new symbol, color, rounded card, shadow or motion was introduced. This is a
visual change; no new product behavior or dependency was added.

The live synthetic preview also shows the new wordmark and collapsed form
sections. Local evidence is in `.local/checks/wordmark-review/`; private records
must remain local. Final local checks passed:227 deterministic Python cases
(9 real TCP,0 skips),27 frontend cases and69 browser cases (0 failures/skips/flaky).
Branch-aware backend coverage85.30%; frontend statements96.52%, branches88.5%.
Lint, types, both builds and all commit hooks exit0; the existing Python resources
package configuration warning remains. Manual screen-reader,400% zoom, other browsers, Linux visual
references and hosted CI remain unverified. No live model or payment call was made.
