"""Reproduce the source-only sample without changing committed files."""

from pathlib import Path
from tempfile import TemporaryDirectory

from research_ops_architecture.models import REFERENCE_DATE
from research_ops_architecture.quality import (
    DataQualityError,
    require_quality,
    run_quality_checks,
    run_staging_checks,
)
from research_ops_architecture.sqlite_mirror import (
    connect_mirror,
    load_synthetic_csvs,
    run_core_and_mart_load,
)
from research_ops_architecture.synthetic import build_synthetic_dataset

ROOT = Path(__file__).resolve().parents[1]


def verify(condition: bool, message: str) -> None:
    if not condition:
        raise DataQualityError(message)


def main() -> None:
    print("Research Ops: synthetic SQLite demonstration")
    print(f"Fixture reference date: {REFERENCE_DATE.isoformat()}")
    with TemporaryDirectory() as first, TemporaryDirectory() as second:
        dataset = build_synthetic_dataset(first)
        build_synthetic_dataset(second)
        files = sorted(Path(first).glob("*.csv"))
        verify(
            {p.name for p in files} == {p.name for p in (ROOT / "data/synthetic").glob("*.csv")},
            "Committed CSV file set differs",
        )
        for path in files:
            verify(
                path.read_bytes() == (Path(second) / path.name).read_bytes(),
                f"Generation differs: {path.name}",
            )
            verify(
                path.read_bytes() == (ROOT / "data/synthetic" / path.name).read_bytes(),
                f"Committed fixture differs: {path.name}",
            )
        print(
            f"PASS: {len(files)} committed CSVs match generation and two runs match byte for byte"
        )
        for name, count in sorted(dataset.row_counts.items()):
            print(f"  {name}: {count}")
        conn = connect_mirror()
        try:
            load_synthetic_csvs(conn, first)
            require_quality(run_staging_checks(conn))
            run_core_and_mart_load(conn)
            require_quality(run_quality_checks(conn))
            for check in run_quality_checks(conn):
                print(f"PASS: {check.name} ({check.detail})")
            print("Lifecycle facts by status:")
            for row in conn.execute("""
                SELECT current_status, COUNT(*) AS requests,
                       SUM(outstanding_authors) AS outstanding
                FROM mart_fact_request_lifecycle GROUP BY current_status ORDER BY current_status
            """):
                print(
                    f"  {row['current_status']}: {row['requests']} requests; {row['outstanding']} outstanding approvals"
                )
            print("Completed synthetic requests by workflow (not real performance):")
            for row in conn.execute("""
                SELECT workflow_type, COUNT(*) AS requests, AVG(cycle_time_days) AS mean_days
                FROM mart_fact_request_lifecycle WHERE cycle_time_days IS NOT NULL
                GROUP BY workflow_type ORDER BY workflow_type
            """):
                print(
                    f"  {row['workflow_type']}: {row['requests']} requests; mean {row['mean_days']:.2f} days"
                )
            for sql, expected in [
                (
                    "UPDATE stg_dashboard_exports SET last_exported_at='2026-06-01T00:00:00' WHERE request_id='REQ-0001'",
                    "dashboard exports are current",
                ),
                (
                    "UPDATE stg_approval_events SET event_type='submitted' WHERE event_id='EVT-0001-02'",
                    "request lifecycle paths match current status",
                ),
            ]:
                conn.execute("SAVEPOINT negative_example")
                conn.execute(sql)
                failed = [c.name for c in run_quality_checks(conn) if not c.passed]
                verify(expected in failed, f"Expected failure not detected: {expected}")
                try:
                    require_quality(run_quality_checks(conn))
                except DataQualityError:
                    print(f"EXPECTED FAILURE detected: {expected}")
                else:
                    raise DataQualityError("Quality gate accepted a deliberately invalid fixture")
                conn.execute("ROLLBACK TO negative_example")
                conn.execute("RELEASE negative_example")
            require_quality(run_quality_checks(conn))
            print("PASS: original fixture restored after negative examples")
            print(
                "This command runs SQLite; SQL Server integration runs separately. All records are synthetic."
            )
        finally:
            conn.close()


if __name__ == "__main__":
    main()
