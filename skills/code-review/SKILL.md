---
name: code-review
description: use when the human requests review of a GoalGuard change or readiness assessment.
---

# code-review

## Trigger

Model-invoked when this task matches an authorized request. This keeps the
engineering workflow active without a separate command; it grants no new authority.

## Process

1. **Bound:** inspect Git status/diff and the agreed spec; preserve uncommitted work and identify the exact review scope.
2. **Trace:** follow inputs, actor authority, state transitions and error recovery. For payment changes, follow [architecture](../../agent_docs/architecture.md) to financial semantics.
3. **Verify:** run the baseline and appropriate completion gates; stop feature work if red and distinguish tool/environment blockers from defects.
4. **Report:** prioritize actionable findings with file/line, failing scenario and impact. State coverage limits and unresolved decisions; do not silently implement the review.

## Done checklist

- [ ] Findings cite observable behavior; passing fixtures are not presented as live proof.
- [ ] Human review retains final responsibility; no correctness guarantee is inferred from a model verdict.
