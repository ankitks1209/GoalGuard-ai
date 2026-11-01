# Engineering setup verification

## Initial connected owner workspace — 22 October 2026

The complete pre-change baseline passed **220/220, zero skips, nine TCP checks**
through approved localhost execution. The six-test frontend baseline also passed.
Focused regressions were observed red before implementing frontend unlocking,
owner overview/static serving, plan preview/confirmation, exact consent and
pending-operation refresh. Additional regressions reproduced late-response
session races, missing affected-purchase IDs and retained private purchase DOM
after locking; each correction passed its focused/full checks.

The initial light owner workspace now connects manual plan setup, exact-cart
review and the timeline on the Python API origin. Sessions retain unsaved
non-secret form input, clear loaded purchase/permit data on lock, and never replay
mutations. The owner-only overview restores existing consent permits and operation
identities for deliberate continuation; it grants no new consent.

Current local gates all exit zero: Ruff; mypy (23 source files); **222/222 backend
tests, zero skips, nine TCP checks**; report validation; **85.30% Python branch-aware
coverage**; Python sdist/wheel build; frontend lint/typecheck/**24 tests**/coverage/
build; all commit hooks; whitespace validation. Frontend coverage is **96.37%
statements, 88.09% branches, 100% functions and 97.64% lines**. Tests are fixture/
deterministic evidence. Setuptools still emits the existing resources package-list
warning; the build succeeds with resource files included.

Actual browser inspection at the available compact viewport verified unlocking,
exact-cart review, keyboard consent/approval, its timeline event, logout,
re-unlock with an unsaved plan-name edit retained, and restoration after the real
session expired. The disposable synthetic preview has no model or PayPal provider
configured. Its 15-minute reservations expired normally; re-unlock showed $350
available, $250 protected and no remaining commitment. The ledger, rather than
session expiry, controls those reservation deadlines.

Broader viewport/accessibility review, hosted CI, a new combined provider flow,
AI-draft UI and paired financial-event forms remain pending. API/CLI access to
drafting and cash events is unchanged. No dependency additions, live provider
requests, commits or pushes occurred in this implementation.

## Owner-session backend verified — 22 October 2026

The sandboxed minimal bind failed with `PermissionError`; the same minimal check
passed through approved escalated execution. The full baseline then passed:
**206/206, zero skips, eight TCP checks**, Python 3.14.7. No feature code was
started before that baseline passed. This does not establish that project
configuration changed the sandbox's effective permissions.

Token exchange was observed red (`404 != 200`), as was a browser-marked bearer
mutation that previously bypassed request protection (`200 != 403`). The backend
now issues opaque fixed-30-minute owner sessions with HttpOnly/Strict cookies,
session-bound CSRF, expected Origin/Host checks, logout and restart invalidation.
Existing non-browser bearer clients remain supported. Tests exercise agent denial,
exact-cart consent and ledger independence. A fixture lost-capture response remains
committed through session expiry; deliberate refresh after unlocking reconciles
the original operation without another capture. This is synthetic evidence.

Current verification: Ruff and mypy (23 source files) pass; the complete suite and
branch-coverage run pass **220/220, zero skips, nine TCP checks**; strict evidence
validation passes; aggregate branch-aware coverage is **84.96%**. Isolated sdist
and wheel builds pass after approved network access for the declared build
dependency. Setuptools warns about the existing resources package configuration;
the wheel includes the resource files and new session module. All configured
commit hooks pass. The unchanged frontend gate passes its six tests, lint,
typecheck, scaffold coverage and static build.

Frontend unlocking, non-secret form retention, deliberate retry controls, static
serving and the three owner screens remain pending. No actual browser acceptance,
new model/payment run, hosted CI, commit or push is claimed. Private session
evidence and the coverage report are retained locally.

## Patched Vitest verified — 22 October 2026

The owner completed the targeted install: one package added, nine changed,
135 audited, **zero vulnerabilities** reported during installation. The owner
then ran the complete frontend gate: lint/typecheck, six tests and build passed.
Actual files were inspected: manifest, lock and installed Vitest/coverage/mocker
all report 4.1.12. The builder independently reran the full gate successfully;
both dependency-state regressions are now green. Coverage remains 100% of the
two scaffold source files, not owner-feature coverage. The frontend commit hook
also passed after this update.

The separate `fsevents@2.3.3` notice concerns unreviewed install scripts. The
lockfile identifies an optional macOS dependency of Vite. No script approval or
package-manager policy was changed. Native watch mode is not verified; test and
build gates already pass. A standalone post-install registry audit was not run
by the builder, whose network remains restricted; the zero finding comes from
the owner's actual install-time audit output.

Green log and local summary live under `.local/checks/vitest-advisory-20261022/`.
No backend runtime change, fresh backend coverage/build, hosted CI run or product
session/browser/payment verification is claimed in this follow-up.

## Earlier Vitest dependency advisory diagnosis — superseded

The owner audit identifies GHSA-82fw-gwwq-j7x9 in `@vitest/mocker`, propagated
through Vitest and its coverage package (three moderate findings, one underlying
advisory). Official advisory/release documentation confirms a 4.1.11 initial
patch and additional mock hardening in 4.1.12. Target both direct Vitest packages
at 4.1.12; no force update or broader dependency change is needed.

- The existing four-test frontend baseline passed before this correction.
- Two new dependency-state guards were observed red against the actual 4.1.0
  manifest/lock/installed packages. These are version checks, not exploit reproduction.
- The targeted npm update exited 1 with registry DNS failure. Byte comparisons
  confirm the manifest and lockfile did not change; all three installed Vitest
  packages remain 4.1.0. No patch or clean audit is claimed.
- Frontend lint/typecheck and Python Ruff/mypy pass with the new guards, but the
  complete frontend gate is currently blocked. Earlier test/build/coverage passes
  below are historical, not a successful post-update run.

The owner must run the exact targeted install, full frontend check and fresh
audit in [frontend instructions](../frontend/README.md). Saved red/install logs
remain under `.local/checks/vitest-advisory-20261022/`.

## Installed frontend tooling — 21 October 2026

The owner supplied Terminal output with a new **206/206 backend pass**, zero
failures/errors/skips and all eight TCP tests. The embedded report was extracted
and independently checked; private copy: `.local/checks/frontend-installed-20261021/owner-backend-report.json`.
No backend runtime source changed in this tooling follow-up.

The owner installed the frontend dependencies and generated the actual lockfile.
Lint, typecheck, three initial tests, 100% coverage of two scaffold files and Vite
build passed. The install reported **three moderate vulnerabilities**; details
remain pending, because the builder's npm audit request fails DNS resolution.
Neither a clean audit nor a targeted dependency fix is claimed.

The React act-environment flag regression was observed failing (undefined instead
of true), then enabled explicitly in test setup. Builder verification now records:

- **Four frontend tests pass**, with 100% statement/branch/function/line coverage
  of the two scaffold runtime files. No owner-feature coverage is implied.
- Frontend lint, explicit TypeScript check and static build all exit zero.
- The new frontend pre-commit hook passes locally. Configuration validation,
  workflow structure/pinned actions/manifest-lock consistency, Python Ruff and
  mypy (22 source files) pass.
- A lockfile-based `Frontend Node 24` CI job is configured but not run remotely.
  GitHub required checks and clean `npm ci` verification are still unobserved.

Saved red/green logs and hook output remain under `.local/checks/frontend-installed-20261021/`.
Earlier Python coverage/build evidence below remains historical; this turn does
not claim a new Python distribution build or repeat blocked TCP execution here.
The owner interface is still a disconnected scaffold; sessions and owner flows
require implementation, security tests and actual browser verification.

## Earlier frontend tooling preparation — superseded

React/TypeScript/Vite and a light owner dashboard are approved. The human delegated
session selection; the accepted local design is recorded in ADR 0004. A frontend
manifest, TypeScript/Vite config and labelled setup page with three toolchain
smoke checks are prepared. No owner session or owner flow is implemented.

- Backend baseline rerun: **206 run, 198 passed, one listener PermissionError,
  seven skips, zero TCP passed** in the restricted assistant environment. This is
  blocked evidence, not a replacement for the owner's earlier complete pass below.
- Frontend lint/typecheck/test-coverage/build commands each exit **127** because
  Oxlint/TypeScript/Vitest are not installed. Npm registry access previously failed
  DNS resolution here. Dependency installation, generated lockfile, frontend checks,
  CI/hook integration and browser rendering remain pending.
- No domain feature was implemented past the blocked backend baseline. The setup
  page and its checks only prepare the development toolchain; no feature TDD
  sequence or frontend coverage result is claimed.

Run `npm --prefix frontend install`, then `npm --prefix frontend run check` in
the owner's normal Terminal and retain the output. The existing backend baseline
must also be green before owner-feature implementation. See
[frontend setup](../frontend/README.md) for exact versions and limits.

## Latest owner verification — 21 October 2026

All requested local quality gates passed in the owner's normal Terminal:

- **206 tests passed, zero failures/errors/skips, all eight TCP tests passed**.
- Strict evidence checker passed against `.local/checks/tests.json`; that file was
  independently read and validated by the assistant without rerunning the suite.
- **83.99% branch-aware runtime coverage**, including all 18 runtime files.
- Source and wheel distributions built successfully; both pre-commit hooks passed.
- Earlier assistant lint/typecheck and skill/hook validators remain passing.

Pasted Terminal output and the matching files under `.local/checks/` and `dist/`
are the evidence. Provenance still names dirty HEAD 93518ad; this is not a claim
that the committed revision includes these source changes. Private summary/artifact
hashes are stored in `.local/checks/quality-20261021/owner-results.json`.

Artifact inspection confirms the wheel's two draft resources match the source
byte for byte, and the sdist excludes private config, handoffs and the private
builder bundle. The build's `goalguard.resources` namespace warning is non-fatal;
explicit package declaration remains a packaging follow-up. No new build is
claimed after source changes because this step only updates documentation/evidence.

**Subsequent product evidence:** the owner ran `python draft_plan.py --demo`
successfully. The saved record confirms HTTP 200, draft_ready, draft saved and no
activation; one live synthetic extraction is documented in
[plan-draft-demo.json](../reports/plan-draft-demo.json). This is separate from
quality checks and the earlier shopping/PayPal demonstrations.
Do not send actual owner financial records until the recorded data-policy question
is resolved. GitHub required checks/native skill registration remain pending.

## Earlier assistant quality pass — 21 October 2026

The owner supplied a normal-Terminal screenshot showing **160 passed, zero failures,
errors or skips, all eight TCP tests passed**, followed by the strict evidence-gate
success message. This is user-run screenshot evidence, not a new assistant-run result.
The development tools and `.git/hooks/pre-commit` launcher are now present on disk.

Subsequent quality work added 46 offline tests (206 total) and corrected:

- One unused import and ten type-check findings through explicit product types,
  safe narrowing and annotations; no blanket ignores or weakened rules.
- Coverage discovery omitting unimported flat CLI files. A regression failed on
  agent/demo/draft_plan omission and passed after the discovery/report-scope fix.
- Malformed/pending HTTP proposal results being projected into definite denials.
  New failing regressions now pass; unknown write outcomes preserve retry identity.
- Monetary literals followed by sentence punctuation being rejected by owner draft
  extraction. Observed red/green tests accept punctuation and still reject numeric
  prefixes, signed amounts and percentages.

### Actual assistant-run checks after changes

| Gate | Result |
| --- | --- |
| Ruff | Passed: `All checks passed!` |
| Mypy | Passed: `Success: no issues found in 22 source files` |
| Coverage | Passed: **83.86%**, 18 runtime files, statement/branch denominator; CLI files included. This was measured on the restricted run below, not a full integration pass. |
| Complete suite | Exit 1: **206 run, 198 passed, 0 failures, 1 error, 7 skips**, all eight missing HTTP checks are blocked by listener permission denial. |
| Strict evidence validator | Correctly rejected that incomplete report. |
| Pre-commit | Launcher exists; manual run passes lint and fails the full-test hook on the same listener restriction. |
| Hook YAML | `pre_commit validate-config` passed. |
| Six official skill metadata checks | All passed now that dependencies are installed. |
| Build | Blocked: normal isolated build cannot fetch its build dependencies here. Diagnostic no-isolation build also cannot import setuptools, which is not persistently installed in the venv. No successful build is claimed. |
| Whitespace | `git diff --check` passed. |

Private reports/logs: `.local/checks/quality-20261021/`. Historical public snapshots
remain untouched. These new model/transport/drafting tests use synthetic responses;
no new real AI or PayPal calls occurred. Initial plan drafting still lacks live
provider verification. No commit/push or remote branch-setting change occurred.

### Required next step

In the owner's normal Terminal, activate the existing `.venv` and run:

```sh
python -m coverage run evaluate.py --report .local/checks/tests.json --require-tcp
python scripts/check_test_report.py .local/checks/tests.json
python -m coverage report
python -m build
python -m pre_commit run --all-files
```

Send the final results; stop on an unexpected failure. No account/key setup or
dependency reinstallation is requested. Feature work remains paused until the
current 206-test source and build are verified. GitHub required-check settings
remain pending; local hooks do not configure remote merge protection. The spec
also records an unresolved policy conflict: private owner financial text versus
the blanket model-data prohibition in AGENTS. Only synthetic draft inputs are
eligible for provider verification until the human resolves that conflict.

## Historical setup attempt — 20 October 2026

Environment: restricted local assistant execution, Python 3.14.7.
Status: files/configuration implemented; activation and full verification blocked.
No product features were implemented by this setup task. Earlier uncommitted
agent/initial-plan-drafting work is preserved and is not retroactively called TDD.

## Commands run now

Commands used the new `.venv/bin/python`, equivalent to `python` after activation.
Each completion command was attempted independently so one blocked tool could not
hide another failure. Private logs are in `.local/checks/engineering-setup/`.

| Command/gate | Actual result |
| --- | --- |
| `python3 -m venv .venv` | Passed. |
| `source .venv/bin/activate` | Verified separately; commands use the venv interpreter. |
| `python -m pip install -e '.[dev]'` | Exit 1: package installation cannot obtain `setuptools>=77` for the isolated build. Earlier direct dev-tool installation also found no Ruff distribution. No tools installed. |
| `python -m pre_commit install` | Exit 1: `pre_commit` module unavailable; hook not installed. |
| `python scripts/pre_commit_tests.py` | Exit 1: 160 discovered/run; 152 passed, 0 failures, 1 error, 7 skipped. Local listener permission denial causes the HTTP error/skips. All eight TCP checks remain unverified here. |
| `python -m ruff check .` | Exit 1: Ruff module unavailable. Source lint result is unknown. |
| `python -m mypy` | Exit 1: mypy module unavailable. Source type result is unknown. |
| `python -m coverage run evaluate.py --report .local/checks/tests.json --require-tcp` | Exit 1: coverage module unavailable; no coverage report generated. |
| `python scripts/check_test_report.py .local/checks/tests.json` | Exit 1 as required: the report is missing. |
| `python -m coverage report` | Exit 1: coverage module unavailable; 80% threshold has not been demonstrated. |
| `python -m build` | Exit 1: build module unavailable; packaging remains unverified. |
| `python -m pre_commit run --all-files` | Exit 1: pre_commit module unavailable. |
| Focused quality-gate unit tests | Observed red before implementation (new module missing); after implementation, 5 tests passed. This is scaffold red/green, not a claim that every branch was independently observed red. |
| Contract and syntax checks | Passed: Python AST, TOML parsing, AGENTS <150 lines (88), CLAUDE import, six concise skill structures and local reference links. |
| `git diff --check` | Passed at verification; repeated after final documentation edits. |
| Bundled skill validator | Could not start: PyYAML unavailable. Structural/link checks above passed; official validator is not reported as passed. |

The initial baseline before infrastructure edits had 155 tests: 147 passed,
1 HTTP error and 7 HTTP skips. The final 160 includes five new gate tests.
The old committed 155-pass snapshot is historical and is left untouched.
No live PayPal/model calls or remote CI run occurred during this setup.

## Contradiction audit

Resolved:
- Replaced the old tests-only-on-request instruction with the new baseline/TDD workflow.
- Corrected the preserved private builder reference from two revisions to one and
  removed mandatory budget inspection. Shopping tools retain least privilege.
- Clarified the public architecture: a real sequential model scenario exists;
  initial plan drafting is implemented but not live-verified, and no owner UI exists.
- Kept AGENTS short and public-ready while private handoffs and the old bundle stay
  ignored. A root `.gitignore` negation makes AGENTS eligible for normal Git tracking.
  Protected `.git/info/exclude` was not edited after approval rejected that mutation.

Remaining discrepancies/limits:
- Required green baseline versus this environment's denied listeners: feature work
  stays stopped. No skip exemption was added.
- CI configuration versus demonstrated enforcement: tools/coverage/remote jobs are
  unverified; Git hook activation and GitHub required-check rules remain pending.
- Skill invocation intent versus native registration: skills are linked in AGENTS,
  not registered in the native `.agents/skills` or `.claude/skills` directories.
- Tests-first agreement versus pre-existing feature code: new agreement applies
  going forward; prior work needs coverage and review before release.
- AGENTS/spec/new skills agree on the workflow and money authority; financial
  equations remain in one maintained contract, not copied into prompts.

## Next concrete actions

On the owner's normal Terminal, from the repo root, activate `.venv`, install
`.[dev]`, install pre-commit, and run every AGENTS completion command. This avoids
the assistant environment's package/listener restrictions, without weakening gates.
Resolve actual lint/type/coverage failures before resuming features. Do not assume
those gates will pass once tools install: existing modules may expose adoption debt.

Before merging, commit the reviewed setup and configure GitHub required checks
for both Python jobs plus the human review policy. No commit/push/settings mutation
was performed here. Native skill menu registration is optional; AGENTS links are available now.

## Still needed from the human

No further product answers are required for this infrastructure setup. Activation
requires a normal Terminal run and GitHub repository settings access. Product work
still needs the OPEN QUESTION decisions in [spec](../docs/spec.md): UI/frontend,
owner browser sessions, evaluation matrix/counts, extra critical coverage targets,
provider expansion and hosting/retention. Ask only when the next task depends on them.
