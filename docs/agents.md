# Real model callers

**Status:** two real Flash-Lite callers completed one sequential shared-budget
scenario through the scoped HTTP API: Agent A reserved a $220 microphone; Agent B
was denied a $180 vacuum and recovered with the $100 alternative. Final capacity
was $30 available, $320 reserved and $0 spent. Both callers used the same model.
Earlier incomplete Gemini 3.8 Flash attempts are retained. See
[observed runs](../reports/gemini-demo.json); no controlled success rate is claimed.

Run these commands from a source checkout, using Python 3.11+. The new caller
uses the standard library. It does not execute PayPal payments.

## 1. Configure model access privately

Create a Gemini key in [Google AI Studio](https://aistudio.google.com/apikey).
Create `.env.models` locally with these entries:

```dotenv
GEMINI_API_KEY=
GEMINI_MODEL_A=gemini-3.8-flash
GEMINI_MODEL_B=gemini-3.5-flash-lite
```

Fill the key yourself and keep this file out of Git. Environment variables take
precedence over file entries. The parser never executes shell expressions.
Model IDs are configurable: confirm availability and quota in your account.
The two suggested IDs appeared in the official free-tier pricing on 18 October
2026; account eligibility and future availability are not guaranteed. Do not
enable paid billing merely to run this prototype.

Google describes free-tier content as usable to improve its products. Use
synthetic shopping requests for this demonstration. The agent tools exclude
private financial records, but your request text is still sent to the model.
See [pricing](https://ai.google.dev/gemini-api/docs/pricing),
[rate limits](https://ai.google.dev/gemini-api/docs/rate-limits) and
[API keys](https://ai.google.dev/gemini-api/docs/api-key).

Inspect configuration presence without making an API request:

```sh
python agent.py --check-config
```

Check key access and list currently advertised generation models with one metadata
request (no shopping task, server tokens or model generation):

```sh
python3 agent.py --list-models
```

This uses [Google's model-list endpoint](https://ai.google.dev/api/models#method:-models.list).
It does not prove generation quota or free-tier eligibility. If `list_complete`
is false, absence from that page is not proof that a model is unavailable.
`model_dns_unavailable` means the hostname could not be resolved; the request did
not reach Google's API. Run the check in your own Terminal if the agent execution
environment blocks networking. The command prints no key or raw provider error.

## 2. Start the existing gateway and confirm a plan

### Quick isolated demonstration

After the model-list check succeeds, run both configured models with automatic
synthetic setup:

```sh
python3 agent.py --demo
```

Progress is printed for each model request/response, including failures. The
network timeout defaults to 60 seconds per request and can be set from 10 to 120:

```sh
python3 agent.py --demo --timeout 90
```

The first run's generic transport error did not identify its cause. A longer
timeout is a bounded troubleshooting adjustment, not proof that it fixes the
failure. Further runs retain the original failed evidence.

The next observed attempt timed out after 60 seconds on its first request with
no tool calls. To isolate the other configured model without repeating the
failing first caller:

```sh
python3 agent.py --demo --only-agent agent-b
```

This makes actual requests with `GEMINI_MODEL_B`. A `completed` result in this
mode covers only the requested agent; it is not a two-agent or denial-recovery
pass. Both earlier failures remain part of the evidence.

That isolated Flash-Lite run succeeded. To run two separately scoped agents
with the demonstrated model, temporarily override Agent A for this command:

```sh
GEMINI_MODEL_A=gemini-3.5-flash-lite python3 agent.py --demo
```

This does not change `.env.models`. Both callers use the same model with
different agent identities/tasks and shared allocation. It can demonstrate
cross-agent coordination; it does not prove two-model or vendor compatibility.
The combined command completed once with actual denial recovery as described
above. It is not a repeated reliability result or a concurrency evaluation.

This source-checkout command creates a **new disposable synthetic household**,
confirms the sample plan in trusted setup code, starts the scoped API on an
available loopback port, and runs microphone then vacuum requests sequentially.
It does not read existing financial state or PayPal configuration. No payment
adapter is constructed and no purchase is approved or paid.

The models choose their own actions. The report records whether a denial and
recovery actually occurred; a model choosing a cheap product immediately does
not count as denial recovery. Two reservations plus no provider errors mark only
this demonstration complete. They do not establish a concurrency result,
baseline comparison, ablation or full milestone pass.

Private per-agent and session JSON files are saved under
`.local/agent-demos/<run-id>/`. The temporary ledger and all demo reservations
are discarded when the process exits; the recorded purchase IDs cannot be used
for subsequent checkout. Each run has fresh synthetic state, which must not be
presented as a way to reset a real household's quota. The command uses actual
model quota, retains the existing per-agent bounds, and stops on a provider
error without switching models or enabling billing. Reported cost remains
unknown. Actual observations and their limits are recorded above.

### Persistent development session

Follow [Getting started](getting-started.md) to start `server.py` and confirm an
owner financial plan. Use the same `--state-dir` for server and caller. Omitting
it from both uses their shared temporary default. Do not reset an existing
ledger or rotate credentials to obtain fresh spending capacity.

Only `agent-a` or `agent-b` credentials are passed to the shopping client. The
model gets neither those tokens nor the owner credential. Connections are
restricted to `127.0.0.1` on the configured port, with redirects disabled.

## 3. Submit real requests

```sh
python agent.py --agent agent-a --request "Find a USB microphone with headphone monitoring; prefer the standard model, but consider a cheaper equivalent if necessary."
python agent.py --agent agent-b --request "Find a floor-cleaning vacuum; prefer the standard model, but a compact equivalent is acceptable."
```

These are two separate callers/configurations, not evidence of two independent
model vendors. Each uses the same gateway with a different authenticated agent
scope. Sequential runs are not a concurrency evaluation.

The loop exposes catalog, proposal and own-purchase status tools. The model can
discover the `propose-purchase` skill through `get_skill`; it reads the denial
reference only when needed. All tool calls, including skill reads, count toward
the eight-call allowance. One revised proposal is allowed. After a terminal
result the host permits at most one tools-disabled explanation. The total model
request cap is nine, with 2,048 maximum output tokens per request. Hidden thought
parts are not recorded; opaque protocol signatures stay in process memory.

The gateway validates prices, merchant, policy, consent and ledger accounting.
The caller has no approval, checkout, capture, void or owner-plan tools. A model
statement that it bought something does not establish a payment or reservation;
use `outcome` and `last_proposal` from the trusted host report.

## Records and failures

Each invocation writes a private `0600` JSON record under
`.local/agent-runs/`, excluded from Git. Do not commit raw requests/transcripts.
Sanitize selected evidence separately. `--record` accepts a new private path
outside the repository or inside `.local/`; existing records are never replaced.

Records include actual model/version, visible messages and tool results, prompt,
tool and skill hashes, token usage, duration, source revision/dirtiness and stop
reason. Token counts are not a billing receipt; cost stays unknown until account
tier and actual usage are checked. A failed model call is recorded as a failure.
An interrupted process can leave a `started` record; it is not a completed run.

- `model_auth_failed` / `model_access_denied`: check your key and account access.
- `model_not_available`: choose a model your project can access.
- `model_rate_limited`: stop and inspect quota; there is no automatic retry storm
  or silent switch to a paid model.
- `model_dns_unavailable`: check the execution environment's network/DNS access;
  this is not evidence of an invalid API key.
- `model_timeout`, `model_connection_closed`, `model_tls_error`: the request
  timed out, lost the connection or failed TLS respectively. No automatic model
  retry occurs; TLS verification is never disabled. Historical generic transport
  errors cannot be retroactively assigned one of these causes.
- `plan_required` / `plan_not_ready`: the owner must confirm a feasible plan.
- `proposal_limit`: server quota persists across invocations.
- `pending`: the host can retry the same proposal/key during this process. Keys
  are not durable across caller restarts yet. Do not start a replacement purchase
  to resolve an uncertain one; inspect existing state and let its TTL apply.

## Skill design decisions

- **Trigger:** model-invoked because the shopping model decides when purchase
  guidance applies. The host advertises the skill; the model loads its body.
- **Structure:** four steps in `skills/propose-purchase/SKILL.md`; branching
  handling in `references/denials.md`, accessed through a fixed resource name.
- **Steering:** Gather, Propose, Recover, Handoff. Each names an observable action.
- **Pruning:** no duplicated financial arithmetic, provider setup, speculative
  scenarios or generic caution in the skill. Authority and loop limits remain in
  code; skill effectiveness still needs real-run/ablation evidence.

## Remaining gate

Before marking real agents complete: exercise both configurations, record
legitimate denial recovery, verify malformed/unauthorized tool attempts and
privacy boundaries, and add owner-confirmed natural-language plan drafting.
Then run the planned fair baseline and prompt ablations with repetitions. These
adapters alone do not satisfy the milestone or prove meaningful runtime AI.
