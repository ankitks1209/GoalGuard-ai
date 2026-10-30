# Testing and enforcement

## Setup and commands

Run the exact root commands in [AGENTS.md](../AGENTS.md) from an activated `.venv`.
Install `.[dev]` before lint, mypy, coverage, build or pre-commit. Do not install
these tools globally. Python runtime dependencies remain empty. React is an approved
frontend runtime dependency. CI covers Python 3.11/3.14; local verification names its version.

Frontend tools require Node 24 and `npm --prefix frontend ci` using its lockfile.
Run `npm --prefix frontend run check` for frontend lint, explicit no-emit typecheck,
component tests with coverage and static build. The prepared coverage floor is 80%
for each statement/branch/function/line measure, separate from Python coverage.
Application entry-point code remains included. Initial owner-component tests now
cover unlocking/expiry, deliberate retry, plan preview/confirmation, exact-cart
consent, payment-pending controls and timeline states. Transport tests also cover
late replies across session changes. These fixture checks complement deterministic
server security checks and synthetic browser inspection; they are not a live
provider demonstration or a broad device/accessibility audit. The
four initial tests and frontend lint/typecheck/coverage/build previously passed
locally. The generated lockfile is present. Two new dependency-state regressions
failed against Vitest 4.1.0 and passed after the 4.1.12 update; the full six-test
frontend gate is now green locally. The owner's install-time audit reported zero
vulnerabilities. [Frontend README](../frontend/README.md) records the update,
optional script notice and unobserved hosted CI/clean reinstall.

`python scripts/pre_commit_tests.py` runs the existing evaluation harness and then
rejects missing, skipped or incomplete evidence. It requires all eight existing
TCP tests, plus a real owner-session exchange/protection/logout TCP check. Its
private report is temporary. In-memory HTTP checks are useful but
cannot replace real loopback tests. Listener denial must fail, not be hidden.

For coverage, use the exact run/report/check commands in AGENTS. All runtime
modules, including the model transport, drafting and CLIs, stay in the denominator.
Discovery starts from the source root and the report includes `goalguard/*.py`
plus the four runtime entry points (`server`, `demo`, `agent`, `draft_plan`). A
fixture regression ensures unimported CLI files remain at zero in the denominator;
tests and engineering helpers are outside the runtime report scope.
The configured 80% floor combines statement and branch coverage. It is not an
80% guarantee for each module, nor evidence of tested external provider behavior.
Subprocess coverage is not claimed; process-kill tests separately exercise recovery.
Never omit modules or lower the threshold to pass this setup.

## Red → green → refactor

1. Establish the complete green baseline. Stop features on red. Diagnose a baseline
   failure or perform explicitly requested infrastructure/docs work without changing product behavior.
2. Map a human-agreed acceptance criterion to a regression. Run the focused test
   and retain concise failing output before implementing. Prefer a behavioral
   assertion failure; a missing new module is an initial scaffold failure, not
   proof that every eventual branch was tested red.
3. Make the smallest fix, observe green, refactor and run all completion gates.
4. Report commands, exit codes, counts/skips and limits. Existing code predating
   this agreement needs characterization/regression coverage, not a claim of past TDD.

For the new evidence validator, focused invocation is:
`python -m unittest discover -s tests -p test_quality_gate.py -v`.
Other unit tests use the same discovery pattern with the relevant file name.

## Local pre-commit gate

`.pre-commit-config.yaml` uses local `language: system` hooks. After installing
`.[dev]`, run `python -m pre_commit install` once per clone and keep `.venv` activated
for commits. It runs full-repo Ruff and the complete deterministic test/evidence
gate, regardless of changed file extensions. The additional `goalguard-frontend`
hook runs frontend lint, typecheck, coverage and build. Install frontend dependencies
and ensure Node 24/npm are on PATH before committing. It does not modify source automatically.
`python -m pre_commit run --all-files` exercises the same configuration manually.

This is a Git pre-commit hook, not an assistant lifecycle hook. Git installation
writes `.git/hooks/pre-commit`; a configured YAML file alone does not activate it.
Do not bypass hooks with `--no-verify` or `SKIP`. Hooks can still be bypassed by a
caller; remote required checks are the merge boundary.

## CI and enforcement limits

Checks runs lint, mypy, tests/coverage, strict report validation, synthetic probing,
deterministic demo, build and installed-wheel smoke checks. Configure GitHub branch
protection/rulesets to require both Python matrix jobs and `Frontend Node 24` before merge. Workflow YAML
alone does not activate that server-side setting. Require a human review for
architecture/spec decisions; tests do not transfer ownership to the AI.

Ruff currently selects E4/E7/E9/F correctness rules, without bulk formatting.
Mypy checks annotated code and bodies of unannotated functions; it does not yet
require every legacy function to have annotations. No blanket ignores suppress debt.
Type/lint adoption failures must be fixed explicitly before features resume.
Neither CI nor a hook proves the chronological order of test-writing or the
correctness of a test oracle; preserve red/green evidence for human review.

## Assistant integration: checked, not guessed

Official docs checked 2026-10-20:
- [Codex hooks](https://learn.chatgpt.com/docs/hooks): project `.codex/hooks.json`
  or inline config, command lifecycle events; non-managed definitions need trust review.
- [Claude Code hooks](https://code.claude.com/docs/en/hooks): project
  `.claude/settings.json` lifecycle hooks, including `PreToolUse`, are distinct from Git hooks.
- [Git hooks](https://git-scm.com/docs/githooks) and
  [pre-commit](https://pre-commit.com/) specify actual commit-time enforcement.

No assistant lifecycle settings are installed. Tool-name matching is not a robust
way to police all possible Git invocations, and a Stop hook cannot prove TDD.
AGENTS/CLAUDE provide instructions; shared Git/CI gates check the result. Native
skill discovery and its limits are documented in [skills.md](skills.md).

## Evidence boundaries

CI uses synthetic data/fixtures and never needs `.env`, `.env.models` or buyer
credentials. Preserve historical reports; write new verification results under
`.local/checks/` or CI temporary storage. Do not overwrite an actual sandbox report
with replay results. Real model/sandbox runs are separate, explicitly scoped tasks.
See [evaluation](../docs/evaluation.md) and [setup verification](setup-verification.md).
