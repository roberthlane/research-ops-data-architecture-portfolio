"""Build from a scratch source copy, then exercise a clean wheel's console command."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(args: list[str], cwd: Path, env: dict[str, str]) -> None:
    result = subprocess.run(args, cwd=cwd, env=env, text=True, capture_output=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)


def main() -> None:
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    env.pop("PYTHONPATH", None)
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp)
        source = scratch / "source"
        shutil.copytree(
            ROOT,
            source,
            ignore=shutil.ignore_patterns(
                ".git",
                ".venv",
                "__pycache__",
                ".mypy_cache",
                ".ruff_cache",
                ".pytest_cache",
                "*.egg-info",
                "build",
                "dist",
            ),
        )
        run(
            [sys.executable, "-m", "build", "--no-isolation", "--outdir", str(scratch / "dist")],
            source,
            env,
        )
        wheels = list((scratch / "dist").glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError("Expected exactly one built wheel")
        run([sys.executable, "-m", "venv", str(scratch / "venv")], scratch, env)
        binary = scratch / "venv" / ("Scripts" if os.name == "nt" else "bin")
        python = binary / ("python.exe" if os.name == "nt" else "python")
        run(
            [str(python), "-m", "pip", "install", "--no-index", "--no-deps", str(wheels[0])],
            scratch,
            env,
        )
        console = binary / ("research-ops-arch.exe" if os.name == "nt" else "research-ops-arch")
        run(
            [
                str(console),
                "--data-dir",
                str(scratch / "data"),
                "--report",
                str(scratch / "quality.md"),
            ],
            scratch,
            env,
        )
        if (scratch / "quality.md").read_bytes() != (ROOT / "docs/quality-report.md").read_bytes():
            raise RuntimeError("Installed wheel's quality report differs from the committed report")
        for path in (ROOT / "data/synthetic").glob("*.csv"):
            if path.read_bytes() != (scratch / "data" / path.name).read_bytes():
                raise RuntimeError(f"Installed wheel's generated fixture differs: {path.name}")
        # Invalid-input behavior must also work in the installed distribution.
        (scratch / "data/authors.csv").unlink()
        failed = subprocess.run(
            [
                str(console),
                "--skip-generate",
                "--data-dir",
                str(scratch / "data"),
                "--report",
                str(scratch / "quality.md"),
            ],
            cwd=scratch,
            env=env,
            capture_output=True,
        )
        if (
            failed.returncode != 1
            or "authors: CSV file is missing" not in (scratch / "quality.md").read_text()
        ):
            raise RuntimeError("Installed wheel did not report invalid input correctly")
    print("PASS: sdist/wheel build and clean console install, including valid and invalid inputs")


if __name__ == "__main__":
    main()
