"""Exercise actual gate failures, not just a clean generated dataset."""
import sqlite3
import tempfile
import unittest

from research_ops_architecture.quality import assert_quality, run_quality_checks
from research_ops_architecture.sqlite_mirror import connect_mirror, load_synthetic_csvs, run_core_and_mart_load
from research_ops_architecture.synthetic import build_synthetic_dataset


class QualityFailureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        build_synthetic_dataset(self.temp.name)
        self.conn = connect_mirror()
        self.addCleanup(self.conn.close)
        load_synthetic_csvs(self.conn, self.temp.name)
        run_core_and_mart_load(self.conn)

    def test_quality_gate_rejects_mutated_records(self):
        cases = [
            ("UPDATE stg_authors SET request_id='MISSING' WHERE author_approval_id='AUT-0001-01'",
             'authors reference existing requests'),
            ("UPDATE stg_approval_events SET request_id='MISSING' WHERE event_id='EVT-0001-A01'",
             'events reference existing requests'),
            ("UPDATE stg_approval_events SET event_type='submitted' WHERE event_id='EVT-0001-02'",
             'request status transitions are valid'),
            ("UPDATE stg_requests SET completion_date=NULL WHERE request_id='REQ-0001'",
             'required lifecycle dates are present'),
            ("UPDATE stg_dashboard_exports SET last_exported_at='2026-06-28T00:00:00' WHERE request_id='REQ-0001'",
             'dashboard exports are current'),
            ("DELETE FROM mart_fact_request_lifecycle WHERE request_id='REQ-0001'",
             'mart lifecycle fact count matches core requests'),
        ]
        for sql, expected in cases:
            with self.subTest(check=expected):
                self.conn.execute('SAVEPOINT failure_case')
                self.conn.execute(sql)
                failed = [c.name for c in run_quality_checks(self.conn) if not c.passed]
                self.assertEqual(failed, [expected])
                with self.assertRaises(AssertionError):
                    assert_quality(self.conn)
                self.conn.execute('ROLLBACK TO failure_case')
                self.conn.execute('RELEASE failure_case')
        assert_quality(self.conn)

    def test_duplicate_staging_request_rejected_by_primary_key(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.conn.execute("INSERT INTO stg_requests SELECT * FROM stg_requests WHERE request_id='REQ-0001'")

    def test_freshness_accepts_two_days_and_rejects_three(self):
        self.conn.execute("UPDATE stg_dashboard_exports SET last_exported_at='2026-06-29T00:00:00'")
        assert_quality(self.conn)
        self.conn.execute("UPDATE stg_dashboard_exports SET last_exported_at='2026-06-28T00:00:00'")
        with self.assertRaises(AssertionError):
            assert_quality(self.conn)
