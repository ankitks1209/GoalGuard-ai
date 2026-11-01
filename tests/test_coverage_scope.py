"""Untouched entry points must remain in the coverage denominator."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class CoverageScopeTests(unittest.TestCase):
    def test_unimported_cli_files_are_reported_at_zero_coverage(self):
        config = Path(__file__).resolve().parents[1] / "pyproject.toml"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "goalguard").mkdir()
            (root / "goalguard" / "__init__.py").write_text("value = 1\n")
            for name in ("server", "agent", "demo", "draft_plan"):
                (root / (name + ".py")).write_text("value = 1\n")
            (root / "marker.py").write_text("import server\n")
            common = ["--rcfile=" + str(config), "--data-file=" + str(root / "data")]
            ran = subprocess.run([sys.executable, "-m", "coverage", "run", *common, "marker.py"],
                                 cwd=root, capture_output=True, text=True, check=False)
            self.assertEqual(ran.returncode, 0, ran.stderr)
            report = root / "coverage.json"
            exported = subprocess.run([sys.executable, "-m", "coverage", "json", *common, "-o", str(report)],
                                      cwd=root, capture_output=True, text=True, check=False)
            self.assertIn(exported.returncode, (0, 2), exported.stderr)
            files = json.loads(report.read_text())["files"]
            for name in ("agent.py", "demo.py", "draft_plan.py"):
                with self.subTest(name=name):
                    self.assertIn(name, files, "Unexecuted CLI omitted from coverage denominator")
                    self.assertEqual(files[name]["summary"]["covered_lines"], 0)
                    self.assertGreater(files[name]["summary"]["num_statements"], 0)
