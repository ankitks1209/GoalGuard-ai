# Owner interface constraints

## Current selected system — 23 October 2026

The twelve interview steps are complete. **Approved to implement the first screen**:
on23 October2026, the owner replied “proceed” to the final design-lock request.
Treat this as approval of the reviewed system; do not demand a magic phrase.
Pause for owner review after the first budget screen before redesigning further screens.
The chronological interview below preserves rejected/superseded proposals; this
snapshot and the pre-lock review take precedence over their earlier pending text.

- Purpose: safely spendable money first, then exact-cart review; UI changes only.
- Identity: merge Teenage Engineering technical navigation/original line icons
  with Enpower oversized regular typography, offset composition and static grain.
- Feel: calm, clear, reassuring; not flashy, cold or preachy.
- Palette A light: background `#F5F5F1`, ink/action `#20231F`, secondary `#555B51`,
  border `#73776D`, surface/action label `#FFFFFF`. No orange primary button.
  Text contrast on background: 14.54:1 and 6.40:1; action label 15.89:1.
  Semantic success/warning/error tokens alias ink, matching the monochrome state
  specimen; explicit text communicates meaning. No distinct semantic hues approved.
- Instrument Sans 400/500; tabular money. Detail14/body16/nav26px on desktop;
  responsive headline40–70px and amount64–156px; body measure66ch, line-height1.5.
- B split workspace: budget/facts left, requests right; budget then requests on
  phones. Shared left edges; spacing4/8/12/16/24/32/48/64px. Stack at800px;
  compact navigation at420px. At320px, navigation scales down to16px to avoid crowding.
- B softer controls: square content, fields4/actions6/dialogs8px;1px borders;
  restrained shadow only on dialogs; rounded line-icon ends/joins and text labels.
- No transitions, entrances, decorative scroll or blanket hover effects; immediate
  action feedback and explicit pending text. Respect reduced-motion preferences.
- A direct voice: action/object labels; errors explain what happened and recovery;
  empty states explain their cause and next action. Preserve precise financial copy.
- All three existing screens get loading/empty/error/offline states. Retain
  validation/denial, session/cart expiry and uncertain-payment commitment handling.
  Owner requested no additional special cases.
- Step12 **A accepted**:16px body,44px minimum standalone action targets; WCAG2.2AA
  target, visible focus, keyboard/status labels, mobile-first320px reflow; review
  at375/768/1024/1440. These targets are not a conformance claim.

Canonical tokens are in `src/styles/tokens.css`; the application imports them.
Instrument Sans is served locally with its SIL Open Font License; no external
font request is needed. The font and license come from the official Google Fonts
Instrument Sans directory (https://github.com/google/fonts/tree/main/ofl/instrumentsans). [Pre-lock review](design-review.md) records the generic-default critique
and limits. Owner approved exact-pinned Playwright/axe development tools and the
Chromium download. Token guard, synthetic browser tests and CI setup are described
in [enforcement plan](design-enforcement-plan.md). Existing UI violations remain
visible until migration; never exempt them merely to make checks green.

The combined static selected prototype was viewed at1280/375/320px. At320px,
crowded navigation was corrected in the preview/token scale. Desktop font load,
document overflow,50px action height and keyboard focus were checked. Narrow
screens were inspected through actual-width frames; programmatic child overflow
was not verified. Production forms/dialogs, assistive technology and zoom still
need review. After the first implemented screen, stop for owner feedback before
building more screens.


## First-screen feedback — essentials first

On23 October2026 the owner said the stacked name feels too basic and the form
shows too many entries. Owner selected A—essentials first rather than a wizard
or AI text drafting. Show current cash, buffer, next payday and expected income
first. Put bills, savings and plan metadata in native expandable sections. Keep
entered/confirmed values when collapsed and include them in preview/confirmation.
Do not remove required name/timezone validation, infer financial facts, or activate
a plan without the existing exact preview/confirmation. No AI integration added.
Disclosure validation rule: an invalid field must open its containing section
before the browser focuses it; native automatic reveal was not reliable in the
observed Chromium check. Do not bypass required validation.
Owner selected C—connected wordmark: lowercase `goalguard` on one line, using
Instrument Sans400 for `goal` and500 for `guard`. Underline `guard` with the
existing2px ink stroke and4px spacing tokens. Retain26px brand size, navigation
tracking/line-height and the accessible name “GoalGuard”. No separate symbol,
new color or motion. This replaces the earlier stacked name.

## Purchase review layout — A selected

On23 October2026 the owner authorized beginning the Purchase review design pass.
Keep the selected theme, connected wordmark, exact-cart consent, payment action
conditions and all existing data. Static alternatives use the current tokens:

- A—cart + decision (recommended): exact cart/charges left, total/deadline/consent
  right on desktop; cart then decision on phones. Matches the budget split layout.
- B—compact receipt: full-width cart/charges followed by consent below. Linear
  reading order, with more vertical space used per request on desktop.

Owner selected A on23 October2026: implement the cart + decision split, retaining
all stored cart details for active and closed requests. Remove the repeated screen
heading and use flat rules without new colors, card shadows or motion. Use the
existing layout/type/spacing tokens; neither proposal adds the rejected defaults.
Consent and payment control conditions, session handling and backend rules remain.
Unknown/unread purchase data must not be labeled empty or given a zero count;
show loading or unavailable status and offer the existing deliberate refresh.
Owner replied “ok” to the implemented Purchase screen review on23 October2026;
proceed to the Timeline design comparison.

## Timeline layout — A selected

Prepared two static alternatives in the selected light theme:

- A—ledger rows (recommended): a narrow timestamp column and wider event/reference
  column, separated by flat horizontal rules. Time moves above the event on phones.
- B—event trail: a continuous vertical rule with timestamp above each event.
  Taller on desktop; slightly shorter on phones in the four-event specimen.

Both remove the repeated heading and preserve server order, event names,
timestamps and purchase references. No filtering, regrouping, new payment action,
color, shadow or motion is proposed. Neither uses the rejected generic defaults.
Owner selected A—ledger rows. Promote its1:3 desktop column proportions into the
canonical `--timeline-columns` token; stack at the existing800px breakpoint. Keep
the app's existing local timestamp formatting and server event order, including
equal-time records. Static preview UTC formatting is not a product change.
Unknown history remains distinct from a successfully read empty list. Show loading
or unavailable copy and retain deliberate refresh; never imply an empty history
after a failed read. Review the implemented Timeline with the owner next.

## Verification follow-up — 26 October 2026

Owner authorized the responsive/accessibility/CI/build-cleanup plan. The layout
decisions remain unchanged. Navigation items may wrap when enlarged text no longer
fits beside the icons; labels must not overlap neighboring icons. An observed
overlap regression failed before the wrapping fix and then passed. No new visual
tokens or taste decisions were introduced. See [verification report](ui-verification.md)
for the tested matrix and the remaining manual/native-browser/hosted checks.

## Owner forms — 28 October 2026

Owner authorized completing AI drafting and financial-update UI, then explicitly
selected synthetic/sample text only for AI. Reuse the selected theme, native
disclosures and existing spacing/control tokens. Keep these flows collapsed so
the essentials-first form stays compact; no new palette, type, shape or motion.
The AI section is initial-plan only and displays the fixed sample before consent.
Manual entries and existing records never enter its request. Show the extracted
amounts, dates and obligations before separate plan confirmation.

Financial updates use activity, amount and an existing linked record when needed;
the host creates the event ID. Review exact terms and confirm that the activity
already occurred externally. Recording does not move money. Preserve an uncertain
record's ID/terms, read status before deliberate retry and never replay on unlock.
Keep in-memory form state; after reload, inspect Timeline's financial details
before recording again. Timeline retains its selected ledger rows and ordering.

## Collaborative design interview — decision history

The owner requires visual identity decisions together, one step at a time.
The existing interface is provisional. Do not change application code until
the owner explicitly says **“design locked”**. The previous visual delegation
does not authorize new taste decisions during this interview.

Owner confirmed the current task is **UI changes only**. Preserve existing
product behavior, session handling, financial rules and payment lifecycle.
Owner subsequently requested **minimalist** styling. This is an agreed overall
direction, not approval of a particular palette, font, spacing scale or layout.
**Latest decision, 23 October:** owner clarified **merge Teenage Engineering and
Enpower**, rather than choosing either alone. The prior “reverse it” message was
resolved by this clarification; do not treat it as a request to revert or invert
colors. Both references are part of the selected direction. Preserve UI-only
scope, spendable-first organization, no orange on the main button and no
transitions. The current snapshot above records subsequent palette/font/layout
approval; no app coding before the explicit design lock.

For each applicable step, offer 2–3 concrete options, explain the recommendation,
and wait for the owner to pick, mix or reject. Record approved decisions here.
Use standalone static previews for visual choices and inspect actual rendering;
disclose when rendering cannot be verified. Taste calls belong to the owner.
Approved tokens will be kept in the requested `src/styles/tokens.css`; do not
introduce unapproved palette, typography, spacing or component values now.

Interview order: subject → references → personality → one bold element → palette
with contrast checks → typography specimens → layout/density → shape/icons →
motion → voice/copy → states → accessibility/responsiveness. Before locking,
review generic defaults, prepare token/enforcement decisions, and add the agreed
mobile/desktop visual-review rule to AGENTS.md. After the first redesigned screen,
stop for the owner's review before building more screens.

Avoid unless explicitly selected: cream/serif/terracotta combinations; near-black
with a lone neon accent; repeated rounded/shadowed cards and gradient washes;
all-caps overlines everywhere, dot-separated meta strings, decorative arrows and
non-sequential numbering; blanket slide/fade or card-hover effects; untouched
framework component defaults. Flag any proposed option that uses these patterns.

### Step 1 — subject and main-screen job

Owner selected **A — Budget first**: understand what is safely spendable, then
review purchase requests. Primary users remain individual/household owners.

Working product sentence: “GoalGuard helps household owners control AI shopping
purchases while protecting their bills, cash buffer, and savings.” No correction
to the sentence was supplied; do not treat silence as an additional design choice.

### Step 2 — references

Owner requested suggested references. The following research informed the choice:

- **A — YNAB:** category-level budgeting, target progress and priority alerts.
  Sources: [targets](https://support.ynab.com/how-to-use-targets-rk5kkI9ks),
  [home overview](https://www.ynab.com/whats-new/the-great-ynab-remodel).
  Documentation verified; visual style unverified because the browser's
  site-safety policy blocked the screenshot asset host. Do not bypass that block.
- **B — Copilot Money:** a prominent spendable figure and separate review queue.
  Sources: [dashboard](https://help.copilot.money/en/articles/6045480-dashboard-tab-overview),
  [public product examples](https://www.copilot.money/).
  Inspected its public spending/review example. Dark/bright styling, rounded
  panels and all-caps labels overlap patterns the owner wants to avoid.
- **C — Monarch:** overview sections and financial-information prioritization.
  Source: [dashboard examples](https://www.monarch.com/features/tracking#dashboard-content).
  Inspected public product examples. Cream/serif/warm-accent marketing styling
  and rounded-panel composition overlap the avoid list; widget density may
  compete with the single main job.

**Approved reference direction:** Copilot Money for the interface organization
and clarity, combined with Monarch's color/theme direction. The owner explicitly
disliked Copilot's colors. The earlier A+B recommendation was not selected.
Monarch's warm theme direction is the owner's preference after the avoid-list
flag; this does not select the full cream/serif/terracotta combination, fonts,
rounded cards or shadows. Exact palette values await Step 5; typography awaits
Step 6. Do not import either product's calculations, bank integration or
investment features.

Standalone local reference board: `.local/design/references/reference-board.html`.
Inspected screenshots for B/C are included; A has an explicit unverified-visual
notice and official links. No app code or design tokens changed.

### Step 3 — personality

Owner selected **A**: calm, clear, reassuring. Must not feel flashy, cold or
preachy.

### Step 4 — one bold element

Owner selected **A — a prominent safely-spendable amount**. Everything else
stays quiet. This answers the agreed main-screen job directly; it changes visual
emphasis, not financial calculations. The monochrome standalone preview
`.local/design/references/bold-options.html` records the alternatives; its colors,
fonts, spacing and overall page layout are not proposed app tokens.

### Step 5 — first palette proposals (all rejected)

Owner explicitly rejected all three palettes below. Preserve as comparison
history only; none is an approved fallback. Owner then selected revision **C —
both brighter accents and cleaner white surfaces**. This is an approved revision
direction, not an exact palette. These directions do not select a banned
cream/serif/terracotta or dark/neon pattern.

Standalone swatch and sample preview: `.local/design/references/palette-options.html`.
These are original proposals inspired by the inspected Monarch reference, not
sampled or official brand values. A uses deeper coral for readable text contrast.

| Named role | A — Stone & coral (rejected) | B — Mist & rose (rejected) | C — Linen & clay (rejected) |
| --- | --- | --- | --- |
| Background | `#F7F7F5` | `#F3F4F6` | `#F6F3EE` |
| Ink | `#263345` | `#273246` | `#302D2B` |
| Accent | `#B54835` | `#AD3F53` | `#A54830` |
| Success | `#24664C` | `#246754` | `#2B684D` |
| Warning | `#855407` | `#80530C` | `#81520E` |
| Error | `#AF2945` | `#A92528` | `#AC2940` |

A combines a light stone background with warm coral and blue-gray ink; previously
recommended for the approved personality, now rejected. B is cooler and more reserved.
C is the warmest; it explicitly overlaps the cream/terracotta avoid-list pairing.
No serif, repeated rounded/shadowed cards or gradient wash is proposed. A also
retains a muted warm-red accent; the owner's decision must be based on the actual
swatches, not the palette names. No palette is approved yet.

Computed six intended normal-text pairings per option: ink/accent/success/warning/
error against background, plus background against accent for button labels.
All 18 pairings pass the [4.5:1 text threshold](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).
Minimum ratios: A 4.97:1; B 5.28:1; C 5.32:1. Zero failures in these tested
pairings; this is not a complete accessibility audit or permission to combine
arbitrary swatches. Source/calculations are local in `build_palette_preview.py`
and `palette-contrast.json` alongside the preview. Status meaning includes text.

Rendered swatches inspected in the available browser viewport. Fonts, spacing,
borders and sample copy remain temporary comparison scaffolding, not additional
design approvals. Application code and `src/styles/tokens.css` remain untouched.
Wait for the palette decision before Step 6 typography.

### Step 5 — second palette proposals (pending)

Preview: `.local/design/references/palette-round2.html`. Both use the approved
brighter-accent/clean-white direction. Recommend A for its orange warmth closer
to the inspected Monarch example; B offers pinker coral. Neither selects a
listed avoid pattern. Keep the spendable figure as the main emphasis and use
the accent sparingly. These are proposed values, not official Monarch colors.

| Named role | A — White & tangerine | B — White & coral |
| --- | --- | --- |
| Background | `#FFFFFF` | `#FFFFFF` |
| Ink | `#182D3D` | `#182D3D` |
| Accent | `#F57845` | `#FF7669` |
| Success | `#16724B` | `#16724B` |
| Warning | `#805500` | `#805500` |
| Error | `#B22A42` | `#B22A42` |

Contrast calculations: ink/background 14.17:1 in both. Ink/accent button labels
are A 5.17:1 and B 5.43:1. All five intended text pairs per option pass 4.5:1
(ink/success/warning/error on background, and ink on accent). **Failures:**
accent text on white and white labels on accent fail normal-text contrast:
A 2.74:1; B 2.61:1. Prohibit those combinations. Samples instead use dark labels
and dark borders; the accent alone is also below 3:1 against white and cannot
serve as the sole required boundary or focus indicator there. Do not darken the
accent silently to fix contrast. Final components and interaction states still
require verification.

Both swatch sets and button samples were rendered and inspected at the available
browser viewport. Local source `build_palette_round2.py` and unrounded results
`palette-round2-contrast.json` sit alongside the preview. Its fonts, spacing,
borders and copy remain comparison scaffolding. No exact palette selected yet;
no production tokens or application code changed. Wait for A, B, mix or rejection.

### Step 5 — minimalist refinement (core direction accepted)

Owner asked for minimalist styling rather than choosing a round-two palette.
Reduce the preview's visual noise and compare color usage in context, not more
large swatch boards. Standalone `.local/design/references/minimal-options.html`
offers **A — one warm action** (white/dark ink, orange only on the primary action)
and **B — monochrome main screen** (white/dark ink including the action). Recommend
A to retain some Monarch warmth while keeping the approved spendable amount as
the main emphasis. Neither selects an avoid-list pattern. State colors remain
reserved for relevant states, not decorations across the normal view.

Both reuse round-two proposal values for comparison; the orange is not newly
approved. Known contrast: dark ink/white 14.17:1, dark ink/orange 5.17:1; orange
text/white and white labels/orange remain prohibited. Fonts, spacing, shapes and
layout in the static study are temporary and await their respective steps.
Required financial context and consent/payment states must remain available;
minimalism does not authorize deleting functionality. Wait for the owner's color
usage preference; exact palette approval and Step 6 are still pending.

Owner likes A otherwise and explicitly clarified **remove orange from the main
button**. Record the accepted core direction as white background, dark ink and a
dark primary button with white text, using the already displayed neutral values
`#FFFFFF` and `#182D3D` in the selected study. Contrast is 14.17:1 for body text
and button labels. Do not relocate orange to a new element without a later
decision. The six-role palette's semantic colors remain proposals for the states
review; no additional hue is needed in the routine view. The updated standalone
preview shows A with the dark button. Advance to Step 6 typography; final type,
spacing, shape and production token integration remain open. No app code changed.

### Step 6 — typography (pending)

Standalone `.local/design/references/type-options.html` compares two single-family
options: **A — Instrument Sans** (recommended; a softer impression suited to the
calm/reassuring direction) and **B — IBM Plex Sans** (more structured/technical
impression). These descriptions are taste judgments. Sources:
[Instrument Sans](https://fonts.google.com/specimen/Instrument+Sans) and
[IBM Plex](https://www.ibm.com/plex/). Neither selects an avoid-list combination.

Proposed specimen scale: 14/16/20/28/56px; 400/600 weights; body line-height1.5;
paragraph measure max66ch; tabular money figures. The smaller viewport uses48px
for the headline amount. Both use the selected dark main button. Other spacing,
shape, layout and copy are comparison scaffolding. Fonts load from Google Fonts
for this preview only; no dependency installed. No font or scale is approved yet.
Actual browser font readiness/checks passed for both families at both weights;
both rendered specimens inspected at1280px viewport with no horizontal overflow.
Narrow-screen typography and the complete accessibility review remain unverified.

### Reference revision — Enpower Trading (23 October, proposals pending)

Inspected the actual reference hero and the next Solar scene. Observed: very
large regular-weight sans-serif typography, asymmetric composition, a compact
dark navigation bar, a light textured/atmospheric background and thin technical
linework. Its scene transition and 3D/scroll effects are not required by the
owner. The numbered navigation overlaps the avoid list; omit it in proposals.
The texture proposed below is static grain, not a gradient wash. No reference
images or brand assets are copied into the GoalGuard study.

Standalone `.local/design/references/enpower-directions.html` offers two static
GoalGuard adaptations of the same synthetic $600 example:

- **A — strong typography (recommended):** large type and spendable figure,
  offset supporting budget rows, compact dark navigation and quiet paper grain.
  Retains reference character with less scanning effort.
- **B — technical linework:** the same language plus a static allocation diagram
  showing $250 protected, $100 reserved and $250 spendable. More technical
  character, with more visual detail competing for attention.

Neither option selects the listed generic defaults. Both keep the primary action
dark, include no animation/transition, and change no financial behavior. Exact
neutral colors (`#F5F5F1`, `#20231F`, `#FFFFFF`, `#73776D`), Instrument Sans, scale,
grain, composition and copy are proposal-only; the old Step 6 choice is paused
for this reference reaction. Prior neutral choices do not force the new reference
to stay bare. Do not treat either option as selected before the owner's response.

Rendered both studies at1280px, checked Instrument Sans loaded and no document
horizontal overflow. Narrow rendering and full accessibility remain unverified.
No app code, dependencies or production tokens changed. Wait for A/B/mix/reject
before refining the typography/layout decisions. Preserve the explicit design
lock requirement and first implemented-screen review.

### Eleken collection comparison — recommendation only (23 October)

Owner requested the best fit from [Eleken's 50 examples](https://www.eleken.co/blog-posts/best-website-design-examples).
Reviewed the collection and directly inspected the live Teenage Engineering and
Depo Studio homepages, supplementing the already inspected Enpower hero/Solar
scene. These are design judgments, not measured usability results or claims that
all 50 live sites were tested.

1. **Enpower Trading (#30), recommended primary visual reference:** large regular
   sans type, quiet light surfaces, strong hierarchy and compact dark navigation.
   Use a static adaptation and keep finance controls easy to find. Of the existing
   studies, recommend A. Do not copy numbered navigation or scene transitions.
2. **Teenage Engineering (#37), secondary technical reference:** useful fine-line
   icon/structure language. Its inspected current homepage has a dark promotional
   product scene and an elaborate navigation treatment; do not import that as
   GoalGuard's main working-screen layout or change the chosen light direction.
3. **Depo Studio (#16), alternative for grouping:** structured asymmetric tiles
   and strong typography. Inspected current collage uses multiple colors, rounded
   panels and a prominent arrow, overlapping avoid-list concerns. The full collage
   would compete with the budget/review job; not recommended as the primary style.

Recommended combination remains Enpower's static visual character with the
previously chosen Copilot information organization, dark main action and existing
financial behavior. This is a recommendation awaiting the owner, not approval of
study A, exact tokens or a design lock. Research screenshots of the two additional
homepages are local `teenage-home.png` and `depo-home.png` beside the study.

### Primary theme selected — Teenage Engineering (23 October)

Owner explicitly said “Teenage Engineering use this as theme overall”. Treat
this as the selected primary reference, not the secondary role in the historical
comparison above. Do not ask the owner to approve the same reference again.
The inspected reference homepage is dark with precise thin typography, technical
line icons and structured navigation. Its overall visual language supersedes the
older light Enpower/Monarch palette assumptions; functional requirements remain.

Standalone `.local/design/references/teenage-direction.html` translates that
language into a proposed dark monochrome GoalGuard screen: large spendable
amount, fine-line navigation icons, squared structure, supporting cash/protection/
reservation figures and a dark primary action with a light label. Icons are
original static SVGs, not copied brand assets. No transitions or animation.
No neon accent, all-caps overlines, repeated rounded/shadowed cards, gradient
washes or decorative numbering is introduced. Dark alone is not the avoided
near-black-plus-neon combination. Preserve the no-orange-button decision.

Exact neutrals, IBM Plex Sans, type weights, icon details, spacing and layout in
this study are proposals. Reuse of earlier font candidates does not approve one.
Keep semantic state colors open for their review. Inspect the rendering and ask
for reaction to this concrete adaptation before proceeding to later taste choices.
The explicit design lock remains required before application changes.

Preview evidence: IBM Plex Sans loaded; direct1280px and635px renders had no
document horizontal overflow. Also visually inspected the375px phone frame in
`.local/design/references/teenage-responsive-check.html`; its navigation labels
and balance remain readable, figures stack vertically. The browser's read-only
DOM scope did not expose iframe contentDocument, so do not claim a programmatic
no-overflow assertion inside that375px frame. This is static responsive evidence,
not interaction/accessibility completion.

Calculated sample contrast for proposed values: main text/background17.69:1,
secondary text/background7.63:1, button label/fill13.54:1; outer button border
against page3.48:1. Focus, semantic states and final controls remain unverified.
Exact grays (`#080808`, `#171717`, `#F1F1ED`, `#A0A09C`, `#666664`, `#252525`)
are proposed neutrals, not newly approved semantic tokens. No app or production
token edits. Ask what feels off in this adaptation before refining it further.

### Merged reference direction selected — Teenage Engineering + Enpower

Owner explicitly clarified “merge both teenage one and enpower”. This supersedes
the single-reference hierarchy above. Preserve Teenage Engineering's technical
navigation/line icons and combine with Enpower's oversized regular type, offset
composition and subtle static texture. The merged direction is accepted; exact
execution remains a proposal.

`.local/design/references/merged-directions.html` offers the same merged screen
in **A — light blend** (recommended to retain Enpower's light character alongside
Teenage Engineering's structure) and **B — dark blend** (Teenage Engineering's
dark character with Enpower's composition). Links switch only the study palette;
there are no transitions or animations. Both preserve the synthetic600/250/100/
250 accounting example and a dark main button with light label. Neither selects
the listed generic defaults. Font, exact shades, spacing, headline copy and icon
details are unapproved. Do not infer the owner's choice of light or dark from
the merged-reference request.

Both merged palettes rendered and inspected at1280px. Instrument Sans loaded,
document horizontal overflow false, palette switch verified by actual computed
background and screenshots. No narrow-width rendering is claimed for this new
merged layout yet; previous theme checks do not verify it. Body and button solid
text contrast calculated separately; interaction states/full accessibility remain
open. Application code, production tokens and dependencies remain untouched.

Owner replied **“done”** after reviewing the merged study, then explicitly chose
**“a light”**. The merged direction and **A — light blend** are now selected.
Keep the proposed background `#F5F5F1`, ink/action `#20231F`, secondary text
`#555B51`, rules `#73776D` and action label `#FFFFFF` as the approved neutral
reference. No orange button or transitions. Semantic state colors remain open.
Solid-color contrast: main text14.54:1, secondary6.40:1, button label15.89:1.
Do not reinterpret “done” as the explicit “design locked” instruction.

### Step 6 resumed — typography in the selected light blend

Compare the two fonts in `.local/design/references/merged-type.html`: **A —
Instrument Sans** (recommended; retains the merged preview's softer Enpower-like
type) and **B — IBM Plex Sans** (more technical impression). Both use the selected
light palette, identical merged composition and original line icons. Neither
selects an avoided visual combination. Recommendation is a taste judgment.

Proposed scale in context: 14px details,16px body,26px navigation/subheadings,
responsive40–70px headline and64–156px amount; weights400/500, body line-height1.5,
paragraph specimen max66ch, tabular amounts. Existing standalone 14–56px study
is historical; this context specimen reflects the stronger merged reference.
Font and exact scale still await the owner. No new app code or dependencies.
Both selected fonts loaded at400/500 and were visually inspected at1280px;
computed family switch verified, no document horizontal overflow. Smaller text
and numeric glyph specimen also inspected. Narrow rendering and full
accessibility remain unverified for this new specimen.

Owner selected **A — Instrument Sans**. Use this as the single family throughout,
with regular400/medium500 and tabular amounts from the specimen. The light merged
reference remains selected. No further font-choice question is required.

### Step 7 — layout and density (pending)

Standalone `.local/design/references/layout-options.html` compares:

- **A — spacious overview:** technical top navigation; large headline and balance
  on the left, supporting budget facts on the right, purchase requests below.
- **B — split workspace (recommended):** same top navigation; headline/balance and
  budget facts in the left column, purchase requests in the right column on
  desktop. Mobile stacks budget then requests. Keeps requests higher without
  removing the approved large type or key budget facts.

Both use selected Instrument Sans and the selected light palette. No repeated
rounded/shadowed cards, all-caps labels, gradients, decorative arrows/numbering or
motion. A synthetic $100 reserved request is the same data in both studies;
static examples do not introduce new product behavior or consent.

Proposed spacing scale4/8/12/16/24/32/48/64px; left-aligned text and shared column
edges; desktop two columns, mobile one column with budget first. Choice of A/B
and spacing/alignment remains with the owner. No app code or production tokens
changed; wait for this decision before Step8 shape.

```text
A — Spacious overview
[Technical top navigation                 ]
[Headline + balance | Cash breakdown      ]
[Purchase requests below                  ]

B — Split workspace
[Technical top navigation                 ]
[Headline + balance | Purchase requests   ]
[Cash breakdown     | Review cart         ]
```

Both1280px desktop layouts were rendered and inspected, Instrument Sans loaded,
no document horizontal overflow. Split columns measured642px/494px with a48px
gap. Mobile stacking is proposed in CSS but not yet visually verified for this
new layout comparison. Do not claim the earlier theme's mobile evidence covers
it. No full interaction/accessibility audit or runtime gate rerun this step.

Owner selected **B — split workspace**. Use budget/facts left and purchase
requests right on desktop; budget then requests on mobile. Retain left alignment,
shared column edges and the proposed4/8/12/16/24/32/48/64px spacing scale from the
selected option. The new mobile arrangement still needs visual verification.

### Step 8 — shape, borders, elevation and icons (pending)

Standalone `.local/design/references/shape-options.html` compares:

- **A — technical edges (recommended):** square content surfaces and fields,
  2px button corners,4px dialog corners,1px borders, no shadows; original1px line
  icons with square ends/joins and visible text labels. Retains reference precision.
- **B — softer controls:** square content surfaces,4px fields,6px buttons,8px
  dialogs,1px borders; a restrained shadow on dialogs only; original1px line icons
  with rounded ends/joins and visible labels. Routine content has no shadows.

Neither uses repeated rounded/shadowed cards, gradients, decorative numbering or
motion. Static samples retain the selected palette/font and synthetic100USD
reservation. These are shape specimens, not functioning forms or dialogs. Final
dialog focus/dismissal behavior remains to be designed. No shape choice accepted
yet; wait for the owner before Step9 motion. No app or production token edits.
Both specimens rendered at1280px, Instrument Sans load verified, no document
horizontal overflow. Dialog edges, shadow difference and icon strokes visually
inspected including the lower specimen. Phone rendering and functional focus/
dismissal/accessibility remain unverified. Runtime/frontend gates not rerun for
this static design study.

Owner selected **B — softer controls**: square content surfaces,4px fields,6px
buttons,8px dialogs,1px borders, shadow only on dialogs, rounded line-icon ends/
joins with visible text labels. Keep routine content shadow-free. This choice
does not turn the static dialog specimen into a new approved interaction flow.

### Step 9 — motion (carry forward prior owner preference)

Owner previously requested no transitions. Carry that forward rather than
re-asking it: no orchestrated entrance, scroll transitions, decorative motion or
blanket hover animation. Action feedback is immediate; loading/pending states
use explicit status text. Respect prefers-reduced-motion. No animated preview
or new motion choice is required; this is a static direction, not a claim that
final loading/focus/accessibility behavior has been verified.

### Step 10 — voice and copy (pending)

Offer two text-only candidate voices. Neither introduces the avoided all-caps
labels, dot-separated meta strings, decorative arrows or other visual defaults.
Recommend A for the approved calm/clear/reassuring personality. Taste belongs to
the owner. Both use action+object button labels, errors that state what happened
and how to recover, and empty states that explain what will appear.

| Example | A — direct (recommended) | B — conversational |
| --- | --- | --- |
| Button | Save changes | Save my changes |
| Load error | Budget couldn’t load. Check your connection and try again. | We couldn’t load your budget. Check your connection, then give it another try. |
| Empty queue | No purchase requests yet. New agent proposals will appear here. | Nothing to review yet. We’ll show new purchase requests here. |

These are voice specimens, not permission to invent new Save operations or
blindly retry financial mutations. A loading retry in this example is a read.
Preserve exact-cart consent, provider uncertainty and explicit action naming.
No copy choice approved yet; wait before Step11 states.

Owner selected **A — direct voice**. Use concise action+object button names,
errors that state what happened plus how to recover, and explanatory empty states.
Preserve the financial meaning of consent/reservation/payment labels. Do not
reopen this tone choice without new owner steering.

### Step 11 — states (coverage review pending)

Every existing screen—plan setup, purchase review and timeline—gets loading,
empty, error and offline treatments, in the selected direct voice. Static board:
`.local/design/references/state-board.html`. Loading never fabricates a zero
balance or empty queue. Read failures have clearly named reload actions; offline
is not a successful save or a completed payment. This introduces no offline
cache or persistence; session privacy rules remain unchanged.

Existing special cases are required, not optional new behavior: session expiry
requires unlocking/status inspection without replay; expired reservations need
a fresh valid proposal before new consent; uncertain payment results keep the
commitment and refresh using the original operation identity. Preserve inline
validation, denial reasons and pending states. Do not use a generic retry button
to repeat financial writes. Do not claim all offline errors occur before the
server acted. Status verification is required when a write outcome is unknown.

Board uses current neutral palette and selected6px button corners, not newly
approved semantic colors. Neither introduces the avoided visual patterns. Ask
whether any additional screen/state needs special handling; recommend covering
the existing three screens and contracted edge cases without adding new flows.
Do not advance to Step12 until the owner has had that opportunity.
Board rendered at1280px, selected font loaded and no document horizontal
overflow. Loading/empty/read-error rows and lower offline/expiry/uncertainty
copy visually inspected. Mobile rendering and actual recovery/keyboard/live-region
behavior remain unverified; no runtime/frontend gates rerun for this static board.

Owner answered **“no”** to additional special handling. Interpret as no additional
cases requested beyond the three screens and existing contracted edge cases.
Retain the reviewed loading/empty/error/offline coverage; do not invent new flows.

### Step 12 — accessibility and responsiveness (pending)

Standalone `.local/design/references/accessibility-options.html` compares
**A — standard sizing (recommended)**:16px body and minimum44px standalone action
targets, versus **B — larger sizing**:18px body and minimum48px action targets.
Both retain Instrument Sans, selected light palette, softer controls and direct
voice. Larger sizing uses more space; neither introduces avoided visual defaults.

Both target WCAG2.2 AA, not verified conformance: normal text4.5:1, large text3:1,
meaningful nontext boundaries/focus3:1; full keyboard access, visible focus,
labels, dialog focus management and status announcements. Status meaning must
include text. Proposed focus ring2px with3px offset in the accepted ink color.
44/48px touch targets are comfort proposals; AA's target minimum is24px with
exceptions. Sources: [contrast](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html),
[focus](https://www.w3.org/WAI/WCAG22/Understanding/focus-visible.html),
[reflow](https://www.w3.org/WAI/WCAG22/Understanding/reflow.html),
[targets](https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html).

Proposed mobile-first review widths:320px reflow,375/768/1024/1440px representative
checks; current study's layout threshold800px for stacking and420px for compact
navigation. Keep budget first when stacked. Enlarged text/zoom and reduced-motion
behavior need verification; no transitions remain requested. Ask for A/B or
changes to targets before the final pre-lock review. No app code changes yet.
Static sample rendered at1280px, Instrument Sans loaded, no document horizontal
overflow. Computed samples match16px/44px and18px/48px. Keyboard Tab moved from
the labeled read-only field to its button; visible2px solid ring with3px offset
verified by screenshot and computed style. This is only a specimen check; final
app keyboard/dialog, zoom/reflow, phone and assistive-tech coverage is unverified.

## Existing technical and product constraints

React + TypeScript + Vite was approved on 21 October 2026; see
[ADR 0004](decisions/0004-owner-interface-proposal.md). The earlier light,
restrained dashboard choice is historical context; its visual implementation is
now provisional under the interview above. Local-session behavior and financial
authority remain agreed. Do not invent product behavior.

## Agreed surface

Three screens: financial-plan setup, exact-cart approval, and an audit timeline.
Use plain language: distinguish a budget reservation, owner consent, PayPal buyer
approval, authorization and captured spending. Label sandbox/synthetic catalog/manual
fulfilment explicitly. Expose uncertain results and a safe status-refresh action.
Never portray a local reservation as a provider funds hold.

## Acceptance for future UI work

- Label inputs; support keyboard navigation, visible focus and readable contrast.
- Show money with currency and source amounts; preserve integer cents in API data.
- Include loading, empty, invalid-input, denied, failed and uncertain-payment states
  where relevant. Preserve entered data on recoverable errors; do not invent financial defaults.
- Show exactly what owner consent covers. Do not imply that refreshing payment status
  initiates another payment. Define double-submit handling before implementation.
- Keep bills/goals and owner credentials out of shopping-agent responses and URLs.
- Session expiry shows an unlock state, preserves non-secret in-memory form input
  and does not release ledger commitments. Never automatically replay a mutation
  after unlocking; inspect existing status first.
- Verify the actual supported viewport sizes and interactions once the human chooses them.

The initial implementation uses sage/white surfaces, system UI text, a serif
headline, explicit status labels and responsive navigation. The available compact
browser viewport was inspected along with unlocking and keyboard cart approval.
Other viewport sizes and a broader accessibility audit remain unverified. Local
session behavior follows ADR 0004; production authentication/hosting is out of scope.
