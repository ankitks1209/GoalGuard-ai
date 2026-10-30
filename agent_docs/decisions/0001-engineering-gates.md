# ADR 0001: Shared engineering gates

Date: 2026-10-20. Status: accepted direction; local activation/verification blocked.

## Context

The project has deterministic tests and CI but no lint/typecheck/coverage gates.
Existing uncommitted agent/drafting work predates the new tests-first agreement.

## Decision

Keep Python >=3.11, pip, setuptools and the existing unittest/evaluation harness.
Add development-only Ruff, mypy, coverage.py and pre-commit. Run CI on Python
3.11/3.14. Require zero skipped tests, the eight existing TCP checks and 80%
aggregate branch-aware runtime coverage. Do not exclude untested new modules.
Use Ruff correctness rules and mypy `check_untyped_defs`; strict annotations
across legacy code are not claimed. No blanket ignores or lowered thresholds.

The human retains architecture/quality/correctness ownership. Require observed
red → green for subsequent behavioral changes and report existing debt honestly.

## Consequences

New gates may initially fail; repair them before features. A dependency install
failure or denied loopback listener is a blocker, not permission to bypass checks.
Branch protection must require the CI jobs on GitHub to prevent bypassed local hooks.
Coverage cannot establish complete correctness, and CI cannot prove tests were written first.

## Verification

See [setup verification](../setup-verification.md) for actual commands and limits.
