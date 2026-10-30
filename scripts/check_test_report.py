"""Reject incomplete deterministic test evidence; no provider calls or secrets."""

import argparse
import json
from pathlib import Path


def validate_report(report: object) -> list[str]:
    if not isinstance(report, dict):
        return ["Expected an evaluation report object."]
    fields = ("test_cases", "run", "passed", "failures", "errors", "skipped", "tcp_passed")
    if any(type(report.get(field)) is not int or report[field] < 0 for field in fields):
        return ["Required counts must be nonnegative integers."]
    problems = []
    if report["test_cases"] == 0 or report["run"] != report["test_cases"]:
        problems.append("The complete discovered suite must run.")
    if report["failures"] or report["errors"] or report["skipped"]:
        problems.append("Failures, errors and skips all block the quality gate.")
    if report["passed"] != report["run"]:
        problems.append("Every executed test must pass.")
    if report["tcp_passed"] < 8 or report.get("original_five_tcp_passed") is not True:
        problems.append("All eight existing TCP checks, including the original five, are required.")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    try:
        problems = validate_report(json.loads(args.report.read_text()))
    except (OSError, ValueError):
        problems = ["Evaluation report is missing or invalid."]
    for problem in problems:
        print(problem)
    if not problems:
        print("Complete deterministic suite passed; no skipped checks.")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
