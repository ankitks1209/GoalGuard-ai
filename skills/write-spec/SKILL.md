---
name: write-spec
description: use when an authorized change needs product requirements or acceptance criteria before implementation.
---

# write-spec

## Trigger

Model-invoked when this task matches an authorized request. This keeps the
engineering workflow active without a separate command; it grants no new authority.

## Process

1. **Locate:** read [docs/spec.md](../../docs/spec.md), the affected API/financial contract and the user request; identify the specific behavior being changed.
2. **Clarify:** list missing decisions as OPEN QUESTION and ask the human; do not implement a guessed outcome.
3. **Specify:** describe users, core/error/empty flows, scope and observable acceptance criteria; label planned versus implemented.
4. **Record:** update the relevant contract and add a short ADR only for a non-obvious human-approved choice.

## Done checklist

- [ ] Every new behavior has an acceptance criterion and an agreed owner decision.
- [ ] Open questions remain explicit; no feature implementation was smuggled into specification work.
