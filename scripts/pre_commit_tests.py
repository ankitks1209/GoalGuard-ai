"""Run the same complete test and evidence gates used by CI."""

from pathlib import Path
import subprocess
import sys
import tempfile


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix="goalguard-checks-") as directory:
        report = str(Path(directory) / "tests.json")
        result = subprocess.run(
            [sys.executable, "evaluate.py", "--report", report, "--require-tcp"], cwd=root, check=False
        )
        if result.returncode:
            return result.returncode
        return subprocess.run(
            [sys.executable, "scripts/check_test_report.py", report], cwd=root, check=False
        ).returncode


if __name__ == "__main__":
    raise SystemExit(main())
