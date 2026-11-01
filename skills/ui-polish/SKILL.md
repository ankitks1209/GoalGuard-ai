---
name: ui-polish
description: use when improving an agreed owner interface without changing financial or payment behavior.
---

# ui-polish

## Trigger

Model-invoked when this task matches an authorized request. This keeps the
engineering workflow active without a separate command; it grants no new authority.

## Process

1. **Inspect:** read the UI acceptance criterion and [agent_docs/design-system.md](../../agent_docs/design-system.md); inspect the actual interface before editing.
2. **Resolve:** ask about missing design/framework/interaction decisions. Do not invent a system while the design remains OPEN QUESTION.
3. **Red:** reproduce the specific interaction/accessibility defect with a failing check before a behavioral fix; record visual-only evidence when no behavior changes.
4. **Refine:** change only the agreed screen/component; preserve exact-cart consent and distinguish loading, empty, denied, failed and uncertain states.
5. **Check:** exercise the agreed viewports and keyboard path, inspect rendered output and run completion gates; report unverified rendering.

## Done checklist

- [ ] No hidden product behavior or new frontend dependency was introduced.
- [ ] Observed visual/interaction evidence and remaining limitations are stated.
