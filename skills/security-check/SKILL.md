---
name: security-check
description: use when explicitly reviewing GoalGuard trust boundaries, consent, data exposure or payment recovery security.
---

# security-check

## Trigger

Model-invoked when this task matches an authorized request. This keeps the
engineering workflow active without a separate command; it grants no new authority.

## Process

1. **Scope:** read [SECURITY.md](../../SECURITY.md), [docs/spec.md](../../docs/spec.md) and [architecture](../../agent_docs/architecture.md); define actors, assets and permitted review actions.
2. **Trace:** inspect role/token boundaries, input validation, constant-time consent checks, exact-cart binding, expiry, logging and private-data allowlists.
3. **Branch:** for money/concurrency/crash paths, read [docs/financial-semantics.md](../../docs/financial-semantics.md) and [docs/architecture.md](../../docs/architecture.md); for agent leakage, inspect [docs/agents.md](../../docs/agents.md) and its actual tool responses.
4. **Reproduce:** use synthetic data to demonstrate a finding. Add and observe a failing regression before an authorized fix; never send live payments or expose credentials to prove a point.
5. **Report:** run completion gates for fixes, identify residual risks and evidence limits, and leave deployment/acceptance decisions with the human.

## Done checklist

- [ ] No real credential or personal financial data entered a report or fixture.
- [ ] Each finding has a concrete path/impact; missing verification is disclosed.
