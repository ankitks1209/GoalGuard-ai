"""Build a self-contained judging ZIP from the current checkout and built UI."""

import argparse
from pathlib import Path
import subprocess
from zipfile import ZIP_DEFLATED, ZipFile


def main():
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="Path to a new ZIP (existing files are preserved).")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error("Output already exists; choose a new ZIP path.")
    subprocess.run(["npm", "--prefix", "frontend", "run", "build"], cwd=root, check=True)
    assets = root / "frontend" / "dist"
    files = {
        "START-HERE.md": root / "docs/judging.md",
        "LICENSE": root / "LICENSE",
        "server.py": root / "server.py",
        "demo.py": root / "demo.py",
        "scripts/judging_demo.py": root / "scripts/judging_demo.py",
        "frontend/dist/index.html": assets / "index.html",
        "frontend/dist/fonts/InstrumentSans-OFL.txt": assets / "fonts/InstrumentSans-OFL.txt",
    }
    for package in ("react", "react-dom", "scheduler"):
        files[f"licenses/{package}.txt"] = root / f"frontend/node_modules/{package}/LICENSE"
    for pattern in ("goalguard/*.py", "goalguard/resources/*.py", "goalguard/resources/*.json",
                    "goalguard/resources/*.txt", "frontend/dist/assets/*.js", "frontend/dist/assets/*.css",
                    "frontend/dist/assets/*.ttf"):
        files.update({path.relative_to(root).as_posix(): path for path in root.glob(pattern)})
    if any(not path.is_file() or path.is_symlink() for path in files.values()):
        parser.error("A required file is missing or is a symlink; rebuild from the source checkout.")
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "x", compression=ZIP_DEFLATED) as archive:
        for name, path in sorted(files.items()):
            archive.write(path, f"GoalGuard-judging/{name}")
    print(f"Judging bundle: {output}")


if __name__ == "__main__":
    main()
