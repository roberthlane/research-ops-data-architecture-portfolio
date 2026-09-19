from __future__ import annotations

import argparse
from pathlib import Path

from .quality import assert_quality, render_quality_report, run_quality_checks
from .sqlite_mirror import connect_mirror, load_synthetic_csvs, run_core_and_mart_load
from .synthetic import build_synthetic_dataset


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build and validate the research operations data architecture demo.")
    parser.add_argument("--data-dir", default="data/synthetic")
    parser.add_argument("--report", default="docs/quality-report.md")
    parser.add_argument("--skip-generate", action="store_true")
    args = parser.parse_args(argv)

    data_dir = Path(args.data_dir)
    if not args.skip_generate:
        dataset = build_synthetic_dataset(data_dir)
        print(f"Generated synthetic dataset in {dataset.output_dir}")
        for table, count in sorted(dataset.row_counts.items()):
            print(f"  {table}: {count}")

    conn = connect_mirror()
    load_synthetic_csvs(conn, data_dir)
    run_core_and_mart_load(conn)
    results = run_quality_checks(conn)
    assert_quality(conn)

    report_path = Path(args.report)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_quality_report(results), encoding="utf-8")
    print(f"Wrote quality report to {report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

