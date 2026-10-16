"""Run deterministic enforcement checks; never label these live LLM/PayPal evals."""

import argparse
import json
from pathlib import Path
import platform
import time
import unittest


class EvidenceResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.passed_ids = []

    def addSuccess(self, test):
        super().addSuccess(test)
        self.passed_ids.append(test.id())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", type=Path)
    parser.add_argument("--require-tcp", action="store_true")
    args = parser.parse_args()
    suite = unittest.defaultTestLoader.discover("tests")
    count = suite.countTestCases()
    start = time.perf_counter()
    result = unittest.TextTestRunner(verbosity=2, resultclass=EvidenceResult).run(suite)
    original_tcp = ["test_unauthenticated_client_is_denied", "test_two_scoped_http_clients_share_one_budget",
                    "test_agent_http_token_cannot_approve", "test_owner_http_approval_and_agent_read_hide_permission",
                    "test_missing_paypal_is_labeled"]
    tcp_passed = [name for name in result.passed_ids if ".HTTPTests." in name or ".PlanHTTPTests." in name]
    original_tcp_passed = [name for name in tcp_passed if name.rsplit(".", 1)[-1] in original_tcp]
    report = {
        "kind": "local_deterministic_enforcement",
        "test_cases": count,
        "run": result.testsRun,
        "passed": result.testsRun - len(result.failures) - len(result.errors) - len(result.skipped),
        "failures": len(result.failures),
        "errors": len(result.errors),
        "skipped": len(result.skipped),
        "tcp_passed": len(tcp_passed),
        "tcp_passed_cases": tcp_passed,
        "original_five_tcp_passed": len(original_tcp_passed) == 5,
        "skipped_cases": [{"test": test.id(), "reason": reason} for test, reason in result.skipped],
        "seconds": round(time.perf_counter() - start, 3),
        "python": platform.python_version(),
        "live_paypal": "not_run_by_this_suite",
        "separate_sandbox_evidence": "docs/sandbox-results.json",
        "live_llm": "not_run",
        "single_llm_memory_baseline": "not_run",
        "scope": "Local ledger and gateway checks. Adapter tests use handwritten fixtures and offline replay of sanitized actual sandbox responses. No live provider calls in this suite.",
    }
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    raise SystemExit(0 if result.wasSuccessful() and (not args.require_tcp or len(original_tcp_passed) == 5) else 1)


if __name__ == "__main__":
    main()
