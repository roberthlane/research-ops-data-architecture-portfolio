from __future__ import annotations

import argparse
import csv
import sqlite3
from pathlib import Path

from .quality import QualityResult, render_quality_report, run_mart_checks, run_staging_checks
from .sqlite_mirror import (
    InputDataError,
    connect_mirror,
    load_synthetic_csvs,
    run_core_and_mart_load,
)
from .synthetic import build_synthetic_dataset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and validate the synthetic workflow demo.")
    parser.add_argument("--data-dir", default="data/synthetic")
    parser.add_argument("--report", default="docs/quality-report.md")
    parser.add_argument("--skip-generate", action="store_true")
    args = parser.parse_args(argv)
    data_dir, report_path = Path(args.data_dir), Path(args.report)
    results: list[QualityResult] = []
    conn = connect_mirror()
    try:
        if not args.skip_generate:
            dataset = build_synthetic_dataset(data_dir)
            print(f"Generated synthetic dataset in {dataset.output_dir}")
            for table, count in sorted(dataset.row_counts.items()):
                print(f"  {table}: {count}")
        load_synthetic_csvs(conn, data_dir)
        results = run_staging_checks(conn)
        if all(r.passed for r in results):
            run_core_and_mart_load(conn)
            results.extend(run_mart_checks(conn))
    except (OSError, UnicodeError, csv.Error, InputDataError, sqlite3.Error) as exc:
        # Do not reproduce raw cell contents or credential-bearing paths in reports.
        results.append(
            QualityResult(
                "input and database load",
                False,
                f"{type(exc).__name__}: check CSV contract and database constraints",
            )
        )
    finally:
        conn.close()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_quality_report(results), encoding="utf-8")
    print(f"Wrote quality report to {report_path}")
    return 0 if results and all(r.passed for r in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
