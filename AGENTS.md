# GoalGuard engineering contract

GoalGuard is a budget firewall for household owners using AI shopping agents.
It protects bills, a cash buffer and savings contributions while scoped agents
propose catalog purchases. Owners consent to an exact cart; deterministic code
controls the ledger and PayPal sandbox lifecycle. Individuals/households are the
primary audience; agent integrators are secondary. The human owns architecture,
quality and correctness; AI implements the agreed specification.

## Start and continuity

- Read `.local/PROJECT_CONTEXT.md` if present, then inspect Git status and affected files.
  Private handoffs are checkpoints, not evidence of current service or test status.
- Read [spec](docs/spec.md), [roadmap](docs/roadmap.md) and the relevant contract below.
  Resume the recorded next step unless the user changes direction.
- Keep this public contract portable. Keep `.local/`, secrets and private records local.
- Before handoff, update the private checkpoint if present: date, changes, evidence,
  unresolved questions, blockers and next action. Label historical/run-now/skipped/unverified.

## Exact commands (repository root, activated virtual environment)

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
python -m pre_commit install
```

| Gate | Command |
| --- | --- |
| Baseline/full tests | `python scripts/pre_commit_tests.py` |
| Lint | `python -m ruff check .` |
| Typecheck | `python -m mypy` |
| Tests with branch coverage | `python -m coverage run evaluate.py --report .local/checks/tests.json --require-tcp` |
| Reject incomplete evidence | `python scripts/check_test_report.py .local/checks/tests.json` |
| Coverage threshold (80%) | `python -m coverage report` |
| Build | `python -m build` |
| All commit hooks | `python -m pre_commit run --all-files` |

Python >=3.11; pip/setuptools; backend has no third-party runtime dependencies.
Python CI uses 3.11/3.14. Frontend: Node 24/npm, React/TypeScript/Vite.
Frontend setup: `npm --prefix frontend ci` using the repository lockfile.
Commands from the repository root:
`npm --prefix frontend run lint`, `npm --prefix frontend run typecheck`,
`npm --prefix frontend run test:coverage`, `npm --prefix frontend run build`.
`npm --prefix frontend run check` runs all four and is a commit hook/CI job.
Require Python matrix jobs and Frontend Node 24 remotely; see [frontend status](frontend/README.md).
Tests use temporary databases and real loopback TCP; denied listeners block the gate.
Fixtures and synthetic checks make no live model/PayPal calls. Never substitute them
for live verification. New provider runs require a scoped task and private configuration.

## Every task

1. Run baseline tests first; stop feature implementation if red. Report the cause.
   Only diagnose/repair the failing gate or perform explicitly requested tooling/docs work.
2. Read the spec; ask the human about missing or ambiguous product behavior.
3. For behavior changes, add a focused failing test, show its failure, then implement
   the minimum correction and refactor while green. Do not claim retroactive TDD.
4. Handle relevant error, loading and empty states; validate inputs. Use environment
   configuration and keep secrets outside code, logs, model context and commits.
5. Before saying done, run lint, typecheck, full tests, coverage and build; show
   concise actual output/exit status. A blocked or skipped check is not a pass.
6. Report omissions, uncertainty and verification limits. Documentation-only work
   needs no invented failing test; run the documented gates and report blockers.
7. Keep diffs focused on one concern. Ask before adding dependencies or changing
   architecture. Preserve existing uncommitted work and local-only material.
8. Record non-obvious agreed choices as short ADRs in `agent_docs/decisions/`.
9. After the same failure twice, propose a narrow rule/skill change before retrying.
10. For every UI change, view it at mobile and desktop widths and critique it against design-system.md before finishing.

## Never do

- Never give a model owner credentials, private financial records or payment authority.
- Never weaken atomic reservations, exact-cart consent or durable payment recovery.
  Prompts may be ablated; ledger invariants may not. Use integer USD cents.
- Never release an uncertain payment, double-count a purchase, or blind-retry payment I/O.
- Never fabricate product requirements, test counts, live evidence or success rates.
- Never lower coverage, ignore type/lint errors or skip checks merely to make CI green.
- Never publish `.local/`, credentials, account identifiers or the private builder skill;
  rewrite published history; or delete local material for GitHub cleanup.
- Never spawn subagents, schedule work, commit, push or run live payments without
  authorization covering that action. Do not bypass hook or branch protections.

## Context pointers

- [Architecture and authority](agent_docs/architecture.md)
- [Testing, TDD and tool/hook setup](agent_docs/testing.md)
- [UI constraints and unresolved design](agent_docs/design-system.md)
- [Financial semantics](docs/financial-semantics.md), [API](docs/api.md)
- Skills: [write-spec](skills/write-spec/SKILL.md), [tdd-feature](skills/tdd-feature/SKILL.md),
  [code-review](skills/code-review/SKILL.md), [ui-polish](skills/ui-polish/SKILL.md),
  [debug](skills/debug/SKILL.md), [security-check](skills/security-check/SKILL.md).
  Read the applicable skill for the task; [invocation and discovery](agent_docs/skills.md).
- The runtime [propose-purchase](skills/propose-purchase/SKILL.md) skill is for shopping
  agents; it does not authorize builder actions. Existing local builder references
  are preserved; current spec/contracts prevail over their stale guidance.
