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

The application has no third-party runtime dependencies. The `dev` extra installs
the distribution build tool. Run commands from the repository root.

```sh
python evaluate.py --require-tcp
python probe_evaluate.py
python demo.py
python -m build
```

These commands use synthetic data, temporary databases and local TCP. They make
no PayPal or model-provider requests and require no payment credentials.

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
