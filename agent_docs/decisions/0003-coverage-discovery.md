# ADR 0003: Include unexecuted CLI modules in coverage

Date: 2026-10-21. Status: accepted implementation of the existing coverage requirement.

## Context

Coverage's module-name source list found the application package and imported
server module but silently omitted unimported flat agent/demo/draft_plan scripts.
The resulting percentage did not measure the agreed runtime scope.

## Decision

Discover from the repository root and filter the report to all goalguard Python
modules and the four runtime entry points. Keep every entry point in the denominator
when unexecuted. Keep the 80% branch-aware aggregate threshold unchanged.
A synthetic fixture test proves an untouched CLI appears with zero covered lines.

## Consequences and verification

The omission regression failed before the configuration change and passes afterward.
New offline adapter, dispatcher, draft and CLI coverage measures 83.86% on a restricted
206-test run. The listener restriction still prevents an overall suite pass here;
normal-Terminal verification is required. No external AI/payment evidence is inferred.
