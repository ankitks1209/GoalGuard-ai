# Contributing

GoalGuard is an early prototype. The current implementation and remaining work
are listed in the [README](README.md) and [roadmap](docs/roadmap.md).

## Development setup

Use Python 3.11 or newer in a virtual environment, then install the project:

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

The Python backend has no third-party runtime dependencies. The `dev` extra installs
lint, typecheck, coverage, pre-commit and distribution build tools. Run commands from the repository root.

```sh
python -m pre_commit install
python scripts/pre_commit_tests.py
python -m ruff check .
python -m mypy
python -m coverage run evaluate.py --report .local/checks/tests.json --require-tcp
python scripts/check_test_report.py .local/checks/tests.json
python -m coverage report
python -m build
python -m pre_commit run --all-files
```

These commands use synthetic data, temporary databases and local TCP. They make
no PayPal or model-provider requests and require no payment credentials.

Read [AGENTS.md](AGENTS.md) and the [product spec](docs/spec.md) before changes.
Follow observed red → green → refactor for new behavior; stop feature work when
baseline tests fail. Failed/skipped/blocked checks are not passes. See
[testing and hook setup](agent_docs/testing.md) for enforcement limits and
[setup verification](agent_docs/setup-verification.md) for current blockers.
The human retains architecture, correctness and quality ownership.

## Owner frontend tooling

Use Node 24/npm for the approved React/TypeScript/Vite frontend:

```sh
npm --prefix frontend ci
npm --prefix frontend run check
```

The owner-generated lockfile is present. Source currently contains only a labelled
development scaffold; its four initial tests, lint, typecheck, coverage and build passed.
The frontend CI job and commit hook run `check`; hosted execution and required
checks remain unverified. The targeted Vitest 4.1.12 update is installed and all
six tests/full frontend gate pass; the owner install-time audit reported zero vulnerabilities;
see [frontend setup and limits](frontend/README.md).
The Python gates above still apply. No owner flow, browser session or payment
integration is established by the frontend scaffold.

## Changes and pull requests

- Keep a change focused and explain its behavior and limitations.
- Preserve integer-cent arithmetic, atomic allocation, cart-bound consent,
  durable payment intents and conservative handling of unknown provider outcomes.
- Include regression coverage for changed financial or authority behavior.
- Update relevant API or financial documentation when its contract changes.
- Report the command, environment, failures and skips when describing verification.
- Keep credentials, user financial data, runtime databases and consent tokens out
  of commits, issues, screenshots and logs.

The existing source layout is intentional. Use `goalguard/` for application logic,
`tests/` for checks and sanitized fixtures, `prompts/` for model guidance, `docs/`
for maintained documentation, and `reports/` for selected evidence snapshots.
Runtime authority must remain in code rather than prompts or skill instructions.

## Provider evidence

Local fixtures, recorded-response regressions and actual sandbox observations are
different evidence categories. Document them separately. A new live sandbox run
requires operator configuration and genuine buyer approval; CI never runs it.
Sanitize actual responses before adding fixtures. Keep stable aliases across
order, authorization, capture, merchant and request IDs so retries can be inspected.

See [evaluation](docs/evaluation.md), [financial semantics](docs/financial-semantics.md)
and the [security policy](SECURITY.md).
