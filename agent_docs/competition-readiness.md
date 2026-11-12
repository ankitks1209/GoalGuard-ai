# PayPal AI Hackathon readiness

Updated 11 November 2026. This maps the verified submission requirements and
the remaining release work. Postman has been exercised and Astropods account
setup is pending. Channel3 discovery remains outside the agreed catalog scope.

## Official requirements versus project checks

The [official rules](https://paypalaihackathon.devpost.com/rules) require central
PayPal sandbox integration and meaningful AI. Partner tools are optional;
sponsor prizes have additional tool requirements. Submission closes
12 November 2026 at noon PST (13 November at 1:30 a.m. IST). A working build needs complete local run
instructions or hosting, public licensed source, a description and a public
YouTube demonstration under three minutes. The overview also asks entrants to
identify their tools and explain their use. See the
[submission overview](https://paypalaihackathon.devpost.com/).

| Item | Why it is on our plan | Current evidence or gap |
| --- | --- | --- |
| Manual accessibility review | Screen-reader narration and native zoom need hands-on inspection beyond automated assertions | Automated axe, keyboard and reflow evidence exists; native checks remain open |
| Firefox verification | Detect browser-specific interaction failures | Passed in the earlier hosted checkpoint. The current changes still need their own hosted Firefox result |
| Linux/hosted CI | Check the reproducible judging setup outside this Mac | Last hosted green run predates the current changes. Review updated Ubuntu Budget screenshots and rerun the unchanged comparison gate |
| AI drafting and financial-update UI | Complete the agreed owner experience | Browser forms implemented with sample-only drafting and explicit financial-record review; fresh browser-to-model run remains pending |
| Combined AI → consent → sandbox demonstration | Demonstrate the actual product and its authority boundaries | November 3 reached real-model proposal, owner consent and sandbox order creation, then stopped at a payee currency error. October 17 verified capture and void separately |
| Repeated AI evaluation and user feedback | Support reliability and problem-fit claims | Limited model observations exist; repeated comparison and five consented conversations remain project goals |
| Runnable build, description and video | Let judges reproduce and assess the entry | [Local judging build](../docs/judging.md) verified from a clean extraction on macOS at desktop and phone widths. Submission text and a short recording are prepared locally. Publish the source and public YouTube URL before completing Devpost |

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
| Astropods | Sponsor model gateway for shopping tool calls and synthetic plan extraction | Candidate replacement for Gemini. The documented Chat Completions endpoint supports client-defined tools. Account access, model availability and live behavior still need verification. [Sponsor signup](https://paypalaihackathon.devpost.com/details/astropods) · [Gateway API](https://docs.astropods.com/ai-gateway/chat) |
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

## Deadline sequence

1. Publish reviewed submission source through a pull request. Check Python,
   Node and browser results on that revision. The changed Budget visuals need
   Ubuntu reference candidates reviewed before the final screenshot comparison.
2. Upload the reviewed video to YouTube. Add its public URL, the public licensed
   repository and the complete judging instructions to the Devpost form.
3. In parallel, claim Astropods access and confirm the workspace's gateway model
   and usage limits. The documented local development path injects the gateway
   host, credential and model into an authenticated Astropods project. GoalGuard
   still needs the adapter and a scoped live run to verify the replacement.
4. Check the PayPal Business sandbox seller can receive USD, and use a compatible
   Personal sandbox buyer. Then scope a fresh combined run through owner consent,
   buyer approval and the sandbox payment lifecycle. Use the existing
   [PayPal setup](../docs/paypal-setup.md) and preserve sanitized evidence.

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
