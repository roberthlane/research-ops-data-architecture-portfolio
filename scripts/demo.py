"""Reproduce the source-only sample without changing committed files."""
from pathlib import Path
from tempfile import TemporaryDirectory

from research_ops_architecture.quality import assert_quality, run_quality_checks
from research_ops_architecture.sqlite_mirror import (
    connect_mirror, load_synthetic_csvs, run_core_and_mart_load,
)
from research_ops_architecture.synthetic import build_synthetic_dataset

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    print('Research Ops: synthetic SQLite demonstration')
    print('Fixture reference date: 2026-07-01')
    with TemporaryDirectory() as first, TemporaryDirectory() as second:
        dataset = build_synthetic_dataset(first)
        build_synthetic_dataset(second)
        files = sorted(Path(first).glob('*.csv'))
        assert {p.name for p in files} == {p.name for p in (ROOT / 'data/synthetic').glob('*.csv')}
        for path in files:
            assert path.read_bytes() == (Path(second) / path.name).read_bytes(), path.name
            assert path.read_bytes() == (ROOT / 'data/synthetic' / path.name).read_bytes(), path.name
        print(f'PASS: {len(files)} committed CSVs match generation and two runs match byte for byte')
        for name, count in sorted(dataset.row_counts.items()):
            print(f'  {name}: {count}')
        conn = connect_mirror()
        try:
            load_synthetic_csvs(conn, first)
            run_core_and_mart_load(conn)
            assert_quality(conn)
            for check in run_quality_checks(conn):
                print(f'PASS: {check.name} ({check.detail})')
            print('Lifecycle facts by status:')
            for row in conn.execute('''
                SELECT current_status, COUNT(*) AS requests,
                       SUM(outstanding_authors) AS outstanding
                FROM mart_fact_request_lifecycle GROUP BY current_status ORDER BY current_status
            '''):
                print(f"  {row['current_status']}: {row['requests']} requests; {row['outstanding']} outstanding approvals")
            print('Completed synthetic requests by workflow (not real performance):')
            for row in conn.execute('''
                SELECT workflow_type, COUNT(*) AS requests, AVG(cycle_time_days) AS mean_days
                FROM mart_fact_request_lifecycle WHERE cycle_time_days IS NOT NULL
                GROUP BY workflow_type ORDER BY workflow_type
            '''):
                print(f"  {row['workflow_type']}: {row['requests']} requests; mean {row['mean_days']:.2f} days")
            for sql, expected in [
                ("UPDATE stg_dashboard_exports SET last_exported_at='2026-06-01T00:00:00' WHERE request_id='REQ-0001'",
                 'dashboard exports are current'),
                ("UPDATE stg_approval_events SET event_type='submitted' WHERE event_id='EVT-0001-02'",
                 'request status transitions are valid'),
            ]:
                conn.execute('SAVEPOINT negative_example')
                conn.execute(sql)
                failed = [c.name for c in run_quality_checks(conn) if not c.passed]
                assert failed == [expected], failed
                try:
                    assert_quality(conn)
                except AssertionError:
                    print(f'EXPECTED FAILURE detected: {expected}')
                else:
                    raise AssertionError('Quality gate accepted a deliberately invalid fixture')
                conn.execute('ROLLBACK TO negative_example')
                conn.execute('RELEASE negative_example')
            assert_quality(conn)
            print('PASS: original fixture restored after negative examples')
            print('Scope: SQLite subset only; no SQL Server execution, external services, or real records')
        finally:
            conn.close()


if __name__ == '__main__':
    main()
