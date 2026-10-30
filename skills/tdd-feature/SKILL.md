---
name: tdd-feature
description: use when implementing or changing agreed GoalGuard behavior with observed red-green-refactor evidence.
---

# tdd-feature

## Trigger

Model-invoked when this task matches an authorized request. This keeps the
engineering workflow active without a separate command; it grants no new authority.

## Process

1. **Baseline:** run the full baseline command in AGENTS.md. If red, stop feature work and diagnose or report the blocker.
2. **Select:** read [docs/spec.md](../../docs/spec.md) and identify an agreed acceptance criterion. Resolve missing behavior with the human.
3. **Red:** add a focused behavioral test; run it and show the expected failure before changing implementation. Fix setup/import mistakes if they mask the intended assertion.
4. **Green:** implement the smallest change, including relevant invalid/loading/empty/error paths. For money or consent, read [architecture](../../agent_docs/architecture.md) and [docs/financial-semantics.md](../../docs/financial-semantics.md) first.
5. **Refactor:** simplify while tests stay green; run every completion gate in AGENTS.md and report actual output and limits.

## Done checklist

- [ ] Observed red and green are recorded; existing code is not called retroactive TDD.
- [ ] Full gates pass, or the work is explicitly incomplete/blocked; no skipped check is a pass.
