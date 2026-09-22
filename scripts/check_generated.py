"""Verify generated artifacts without modifying them; --write explicitly refreshes them."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import tempfile
from pathlib import Path

from build_dictionary import render

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--write", action="store_true", help="Refresh the committed generated files"
    )
    args = parser.parse_args()
    env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONDONTWRITEBYTECODE="1")
    with tempfile.TemporaryDirectory() as tmp:
        scratch = Path(tmp)
        subprocess.run(
            [
                sys.executable,
                "-m",
                "research_ops_architecture.cli",
                "--data-dir",
                str(scratch / "data"),
                "--report",
                str(scratch / "quality.md"),
            ],
            cwd=ROOT,
            env=env,
            check=True,
            capture_output=True,
        )
        generated = {
            f"data/synthetic/{p.name}": p.read_bytes() for p in (scratch / "data").glob("*.csv")
        }
        if set(generated) != {
            str(p.relative_to(ROOT)) for p in (ROOT / "data/synthetic").glob("*.csv")
        }:
            raise RuntimeError("Synthetic CSV file set differs")
        generated["docs/quality-report.md"] = (scratch / "quality.md").read_bytes()
        generated["docs/data-dictionary.md"] = render().encode()
        # The demo also independently checks committed fixtures and two generations.
        if args.write:
            for name, contents in generated.items():
                (ROOT / name).write_bytes(contents)
        generated["docs/demo-output.txt"] = subprocess.check_output(
            [sys.executable, str(ROOT / "scripts/demo.py")],
            cwd=ROOT,
            env=env,
        )
        for name, contents in generated.items():
            if args.write:
                (ROOT / name).write_bytes(contents)
            elif (ROOT / name).read_bytes() != contents:
                raise RuntimeError(f"Generated artifact differs: {name}; run make refresh")
    print(f"PASS: {len(generated)} generated artifacts {'refreshed' if args.write else 'match'}")


if __name__ == "__main__":
    main()
