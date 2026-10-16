---
name: goalguard-engineering
description: "Implement or verify an explicitly requested GoalGuard milestone: its budget ledger, purchase consent, PayPal sandbox lifecycle, or agent evaluation. Use for this project, not general finance advice."
---

# GoalGuard engineering

## Trigger

User-invoked as `$goalguard-engineering`. This workflow touches payment execution
and project-specific evidence; explicit selection keeps it out of unrelated tasks.
The user delegated the trigger choice through the Skill Checklist Framework.

## Steps

1. **Scope.** Locate the user's GoalGuard project and its instructions. Read the
   current README and evaluation report. Identify the requested milestone, available
   credentials and execution permissions without printing secrets. Preserve the
   verified-local / fixture-only / unverified distinction.
2. **Observe.** Read the affected implementation and reproduce the specific gap.
   Use source inspection for review-only requests; edit only when implementation
   is authorized. Record the failing condition and expected observable behavior.
3. **Enforce.** For ledger, consent or money changes, read the context pointer
   [payment invariants](references/payment-invariants.md). Implement the smallest
   correction that preserves the invariant and trust boundary. Confirm intent is
   durable before sending any money-moving request.
4. **Verify.** Add meaningful checks for the changed behavior and run the applicable
   suite. Use real TCP when permitted. Payment fixtures do not close the live
   sandbox gate; configure credentials locally and retain redacted provider evidence.
   Treat a timed-out payment as unresolved until reconciled.
5. **Recover.** For agent/prompt work, read the context pointer
   [empirical agent workflow](references/empirical-agents.md). Give the model a
   bounded tool loop with structured feedback. Keep consent and settlement in
   trusted code. Compare prompt variants with identical cases before deleting
   instructions or adding scaffolding.
6. **Prune and report.** Remove instructions or abstractions only when observed
   behavior supports their removal. Keep task evidence: changed behavior, named
   checks, denominators, failures/skips, unresolved gate and next action. Do not
   rename the product, schedule maintenance, publish, or broaden the project merely
   because this skill was invoked.

## Reference routing

- Read `payment-invariants.md` only for ledger, approval, provider, or crash work.
- Read `empirical-agents.md` only for agent orchestration, prompts, or eval work.
- Use the project's own commands and evidence files rather than copying its code
  into this skill. Recheck current PayPal documentation when provider behavior matters.
