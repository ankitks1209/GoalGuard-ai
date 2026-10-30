---
name: debug
description: use when diagnosing a reproducible GoalGuard failure or a blocked quality gate.
---

# debug

## Trigger

Model-invoked when this task matches an authorized request. This keeps the
engineering workflow active without a separate command; it grants no new authority.

## Process

1. **Observe:** run the baseline, preserve the exact failure and identify fixture, real-provider or environment scope. Never print secrets.
2. **Isolate:** narrow to the smallest reproducible input/state; distinguish the causal hypothesis from evidence.
3. **Red:** capture the agreed expected behavior in a regression test and observe the failure before changing runtime code.
4. **Correct:** fix the cause with a focused diff. For uncertain payments, read [docs/financial-semantics.md](../../docs/financial-semantics.md) and [docs/architecture.md](../../docs/architecture.md); never probe by creating another payment.
5. **Verify:** show regression green and all completion gates. After two identical failures, propose a different rule/skill or diagnostic instead of repeating.

## Done checklist

- [ ] Root cause or uncertainty is explicit; no speculative broad rewrite.
- [ ] The regression and full-gate results distinguish passed, failed, skipped and unverified.
