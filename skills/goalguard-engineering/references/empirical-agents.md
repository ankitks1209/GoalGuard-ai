# Empirical agent workflow

## Minimal prompt and bounded recovery

Set an outcome, available tools, authority boundary and exit criteria. Do not
repeat financial arithmetic rules in a prompt when code enforces them. The model
can ask for missing requirements, propose catalog candidates and explain returned
trade-offs. It cannot grant consent or settle payments.

Use a bounded loop: inspect budget/catalog -> propose -> read the structured
decision -> revise if a feasible counteroffer exists -> stop for owner review or
report why no solution fits. Suggested initial bounds are eight tool calls and
two revised proposals, made explicit and configurable. Do not retry a successful
reservation with a new key, extend expiry through retries, or retry uncertain
payments from an agent loop.

Escalate ambiguous user goals rather than inventing essential commitments. Return
visible diagnostics and tool evidence; do not request hidden reasoning traces.

## Ablation

On a model/provider/prompt change, preserve the incumbent and compare a minimal
variant on the same scenario list. Optionally remove one hint at a time. Do not
delete production instructions first and reconstruct them by intuition.

Keep fixed catalog, tools, budgets, request schedule and measurement definitions.
Include legitimate tasks and adversarial cases. Record each model/version, prompt
hash, parameters, repetitions, outputs, tool decisions, cost and latency.

Measure accepted policy violations, correct legitimate requests, false denials,
feasible recovery, and completion cost. Adopt the simpler prompt when measured
behavior is no worse under the documented criteria. A newly released model is
not evidence that deterministic controls can be removed.

## Baselines and useful stretch tasks

Compare independent per-purchase checks, one LLM tracking budget in memory, and
the same model using the gateway. Include a sequential updated-memory control
and disclose shared-memory serialization in concurrent cases. Retain baseline
successes. A non-failing baseline is a valid outcome, not grounds to weaken it.

Try harder tasks through the existing tools: a multi-item constrained basket,
ambiguous needs that require clarification, an unavailable product, or overlapping
commitments. Increase task complexity only after ordinary scenarios work. Add
another agent when it has a defined independent role; do not multiply agents as
a substitute for a measurable product need or user authorization.

Prune repeated hints, dead code and duplicate abstractions in the requested scope
after reproducing relevant checks. Do not create recurring jobs or rewrite the
whole repository under the heading of maintenance. New real failure cases should
become focused regression checks.
