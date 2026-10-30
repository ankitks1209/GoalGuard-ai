"""The quality gate must reject incomplete evidence, including skipped TCP tests."""

import unittest

from scripts.check_test_report import validate_report


class QualityGateTests(unittest.TestCase):
    def report(self):
        return {"test_cases": 160, "run": 160, "passed": 160, "failures": 0,
                "errors": 0, "skipped": 0, "tcp_passed": 8,
                "original_five_tcp_passed": True}

    def test_accepts_complete_success(self):
        self.assertEqual(validate_report(self.report()), [])

    def test_rejects_skips_even_when_runner_calls_them_successful(self):
        report = self.report()
        report.update(skipped=1, passed=159)
        self.assertTrue(validate_report(report))

    def test_rejects_missing_tcp_case(self):
        report = self.report()
        report["tcp_passed"] = 7
        self.assertTrue(validate_report(report))

    def test_rejects_partial_empty_or_inconsistent_counts(self):
        for changes in ({"run": 159}, {"passed": 159}, {"test_cases": 0, "run": 0, "passed": 0},
                        {"failures": 1}, {"errors": 1}, {"original_five_tcp_passed": False}):
            with self.subTest(changes=changes):
                report = self.report()
                report.update(changes)
                self.assertTrue(validate_report(report))

    def test_rejects_missing_or_wrongly_typed_fields(self):
        self.assertTrue(validate_report({}))
        for value in (True, "160", -1, None):
            with self.subTest(value=value):
                report = self.report()
                report["passed"] = value
                self.assertTrue(validate_report(report))
