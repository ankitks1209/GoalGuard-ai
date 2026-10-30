# Skill invocation and existing framework

Canonical skills remain in `skills/`. The six new builder skills are model-invoked
when their descriptions match an authorized task; AGENTS directs the assistant to
read the applicable file. This makes the new workflow the default while keeping
step details out of AGENTS. Invoking a skill grants no extra permissions.

The existing `propose-purchase` is a runtime shopping skill: server-owned prices,
one revision, scoped tools and owner handoff. Preserve its denial reference.
The existing local `goalguard-engineering` is user-invoked and stays private.
Its payment-invariant and empirical-evaluation references remain available for
specialized work; its stale inspection/revision advice is aligned to the current spec.

Each new skill uses action words, numbered concrete steps and a done checklist.
Conditional payment/recovery guidance links maintained contracts instead of
copying the old bundled skill. Do not proliferate references without a branch to explain.

## Discovery limits

Current official Codex docs discover repo skills in `.agents/skills`; Claude Code
uses `.claude/skills`. Root `skills/` alone does not install/register them. Explicit
AGENTS links work as instructions but are not a claim of native skill-menu registration.
The native discovery directories are not modified by this setup.
If automatic discovery is required, link the six canonical directories in each
supported location after reviewing workspace permissions; do not link the private bundle.

Sources checked 2026-10-20:
[Codex skills](https://learn.chatgpt.com/docs/build-skills),
[Claude Code skills](https://code.claude.com/docs/en/skills).
