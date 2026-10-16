# Getting started

## Requirements

- Python 3.11 or newer.
- macOS or Linux for the current development workflow.
- No PayPal or AI-provider account for the local demo and checks.

## Install

```sh
git clone https://github.com/ankitks1209/GoalGuard-ai.git
cd GoalGuard-ai
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

The runtime uses Python's standard library. Installation adds `goalguard-demo`
and `goalguard-server` commands. The source scripts work without installation too.

## Run the local demonstration

```sh
python demo.py
```

The demo uses synthetic products and deterministic callers. It shows two purchases
that individually fit a budget but exceed it together, then uses the shared
ledger to reserve one purchase and offer a feasible alternative for the other.
The owner confirms a financial plan and approves a recovered purchase.

Expected initial plan: $600 cash, $100 bill, $50 buffer and $100 savings
contribution leave $350 available. An expected $400 receipt changes the forecast,
not cash authority. Either concurrent proposal may win. The demo makes no PayPal
or LLM requests; its output is not evidence of real-agent behavior.

To write a synthetic plan with current dates for API setup:

```sh
python demo.py --write-plan /tmp/goalguard-demo-plan.json
```

## Start the API

Keep state outside the source checkout, in a private persistent directory:

```sh
mkdir -p ../goalguard-runtime
chmod 700 ../goalguard-runtime
python server.py --state-dir ../goalguard-runtime --env-file .env --port 8765
```

The API listens at `http://127.0.0.1:8765`. On first start it creates a bootstrap
household and scoped credentials in `../goalguard-runtime/tokens.json`.
Every route requires a bearer token. Tokens are not printed to the console;
inspect them privately for your API client. Never give the owner token to a model.

Purchasing stays disabled until the owner previews and confirms a plan through
the [financial API](api.md). There is no owner browser interface yet.
Keep the same state directory across restarts. Do not reset a database with
outstanding authorizations or uncertain payments. The default temporary state
location is suitable only for disposable local rehearsals.

## Enable PayPal sandbox

Follow [PayPal setup](paypal-setup.md), then restart the API with its configured
`.env`. Genuine buyer approval is required before authorization. A localhost
return page may refuse connection because callback UI is unfinished; the owner
workflow verifies approval through PayPal's order API.

## Verification and next steps

```sh
python evaluate.py --require-tcp
python probe_evaluate.py
```

The checks use temporary state, local TCP and fixture transports. They do not
exercise live payment or model providers. See [evaluation](evaluation.md) for the
separate sandbox evidence and [contributing](../CONTRIBUTING.md) for build tools.
Real model integration and the owner interface are tracked in the [roadmap](roadmap.md).
