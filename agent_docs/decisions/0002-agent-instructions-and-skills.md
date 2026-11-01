# ADR 0002: Portable instructions and focused skills

Date: 2026-10-20. Status: accepted; files remain uncommitted.

## Context

The owner wants repeatable engineering sessions and an existing purchase skill
and local engineering skill must survive the setup.

## Decision

Use a short public AGENTS.md and CLAUDE.md importing it. Keep private continuity
under .local. Canonical new engineering skills live in skills/ as requested;
AGENTS links them explicitly. Use model-invoked, task-specific discovery for the
six builder skills so the appropriate workflow applies without another command.
The existing local user-invoked builder skill keeps its invocation policy.
The shopping skill remains model-invoked and does not inherit builder authority.

## Consequences

Canonical skills/ is not automatically discovered by Codex as .agents/skills.
AGENTS supplies explicit context pointers; future automatic discovery can use
reviewed links in the documented product directories without copying instructions.
Do not force-add private notes or change global assistant settings.
Git pre-commit is the shared commit gate; assistant lifecycle hooks are not a substitute.
Root .gitignore explicitly unignores AGENTS.md so the public contract can be
tracked despite the old local exclusion, without editing protected Git metadata.
