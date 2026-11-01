# PayPal AI Hackathon readiness

Checked 27 October 2026. This is a requirements map and proposed work order,
not an eligibility guarantee or evidence of a new provider run. The owner wants
to finish while making useful use of sponsor products. Postman is now exercised;
APIMatic is being assessed. Channel3 scope is not approved by that request.
The empty root `COMPETITION_RULES.md` was preserved.

## Official requirements versus project checks

The [official rules](https://paypalaihackathon.devpost.com/rules) require central
PayPal sandbox integration and meaningful AI. Partner tools are optional;
sponsor prizes have additional tool requirements. Submission closes
12 November 2026 at noon Pacific. A working build needs complete local run
instructions or hosting, public licensed source, a description and a public
YouTube demonstration under three minutes. The overview also asks entrants to
identify their tools and explain their use. See the
[submission overview](https://paypalaihackathon.devpost.com/).

| Item | Why it is on our plan | Current evidence or gap |
| --- | --- | --- |
| Manual accessibility review | Screen-reader narration and native zoom need hands-on inspection beyond automated assertions | Automated axe, keyboard and reflow evidence exists; native checks remain open |
| Firefox verification | Detect browser-specific interaction failures | Local engine fails before page execution; no Firefox pass claimed |
| Linux/hosted CI | Check the reproducible judging setup outside this Mac | Workflow exists; current dirty tree has not run remotely; Linux screenshot references remain open |
| AI drafting and financial-update UI | Complete the agreed owner experience | Browser forms implemented with sample-only drafting and explicit financial-record review; fresh browser-to-model run remains pending |
| Combined AI → consent → sandbox demonstration | Demonstrate the actual product and its authority boundaries | Separate real-model and PayPal demonstrations exist; combined flow is pending |
| Repeated AI evaluation and user feedback | Support reliability and problem-fit claims | Limited model observations exist; repeated comparison and five consented conversations remain project goals |
| Runnable build, description and video | Let judges reproduce and assess the entry | Packaging smoke passed previously; complete judging walkthrough and recording remain pending |

The rules do not prescribe Firefox, Linux CI, a named accessibility test suite,
five interviews or a second model vendor. These are engineering/research goals.
They remain honestly tracked; changing submission priorities does not mark them
passed or remove the repository's required gates.

## Tools and APIs

Recommendations below are engineering judgments about fit. Only the stated
Postman run is new verified tool use. Sponsor credits, other integrations and
prize eligibility remain unverified.

| Tool | Useful role in GoalGuard | Status and proposed next step |
| --- | --- | --- |
| PayPal sandbox | Owner-approved order, authorization, capture, void and reconciliation | Implemented with historical provider evidence; verify a fresh combined flow |
| Gemini | Product selection, bounded denial recovery and consented initial-plan extraction | Implemented with limited real-model evidence; preserve deterministic ledger and owner authority |
| Postman | Reproducible API requests, assertions and judging instructions | Actual CLI 1.80.0 execution passed 18 requests/45 assertions against disposable synthetic state; collection, blank template and instructions in [postman](../postman/README.md) |
| APIMatic | PayPal API context for development of the integration | Official ContextMatic endpoint reached but returned HTTP 401 requiring OAuth; no successful context lookup or integration claim |
| Channel3 | External product discovery and enrichment | Strong product fit, but expands the agreed synthetic catalog; needs an owner decision and a separate discovery/checkout contract first |
| Astropods | Managed agent runtime or model gateway | Optional alternative, not a verified need; account/model access and adapter work remain unverified |
| Render | Hosted judge access | Optional; first review the loopback-only server, persistent state, sessions and deployment scope; no deployment recipe has been validated |

Primary sponsor resources:

- [Postman resources and PayPal collections](https://paypalaihackathon.devpost.com/details/postman)
  and [PayPal's official Postman workspace listing](https://www.postman.com/paypal).
- [APIMatic Context Plugin information](https://paypalaihackathon.devpost.com/details/apimatic).
  The linked getting-started PDF did not expose readable setup instructions in
  this browser fetch; installation has not been verified.
- [Channel3 resources](https://paypalaihackathon.devpost.com/details/channel3).
  Its sponsor guidance requires meaningful API/MCP calls for that tool claim.
  Published credit offers are not evidence of credits in our account.
- [Astropods resources](https://paypalaihackathon.devpost.com/details/astropods)
  and [Render resources](https://paypalaihackathon.devpost.com/details/render).

## Proposed sequence

1. Keep the agreed synthetic catalog while finishing. Postman supports the
   current API; APIMatic requires an authenticated connection before further use.
   Adding external catalog discovery still needs a separate owner decision.
2. Completed first Postman run against disposable synthetic state; see
   [sanitized evidence](../reports/postman-demo.json). Keep environment files and
   raw run records private; no cloud workspace was created or published.
3. Owner forms implemented: sample-only AI drafting, explicit consent, manual
   fallback, exact-plan confirmation and paired financial-event review/recovery.
   See [verification](owner-form-verification.md); no new real-model run claimed.
4. Scope a fresh model → proposal → owner review → PayPal sandbox run. Obtain
   the required live-run authorization, use synthetic finances and manual buyer
   approval, and preserve sanitized evidence. No payment action is authorized by
   this document.
5. Complete the runnable judging instructions, focused evaluation and video.
   Review public artifacts before any authorized publication/submission.

## Decisions still needed

- Channel3 product discovery remains optional and undecided.
- If Channel3 is selected: how may an external discovery result become an
  approved sandbox catalog item? External prices and merchant purchase links
  cannot silently replace server-controlled cart terms or prove fulfilment.
- Local judging setup or a separately scoped hosted deployment?

Verification evidence for the completed UI review remains in
[ui-verification.md](ui-verification.md). Historical test/provider observations
remain historical until explicitly rerun; no live model or payment call was
made during this requirements and API-tool review. The new Postman run is
separate current evidence, not a rerun of the historical model/payment results.
