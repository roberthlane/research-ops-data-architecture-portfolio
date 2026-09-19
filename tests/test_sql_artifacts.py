from __future__ import annotations

import unittest
from pathlib import Path


SQL_DIR = Path("sql/azure_sql")


class SqlArtifactTests(unittest.TestCase):
    def test_sql_scripts_exist_in_expected_order(self) -> None:
        expected = [
            "00_create_schemas.sql",
            "01_staging_tables.sql",
            "02_core_tables.sql",
            "03_mart_tables.sql",
            "04_elt_load_core.sql",
            "05_elt_build_mart.sql",
            "06_views_and_procs.sql",
            "07_indexes_security_backup_notes.sql",
        ]

        self.assertEqual([path.name for path in sorted(SQL_DIR.glob("*.sql"))], expected)

    def test_dimensional_model_tables_are_declared(self) -> None:
        mart_sql = (SQL_DIR / "03_mart_tables.sql").read_text(encoding="utf-8").casefold()
        for table in [
            "mart.dim_date",
            "mart.dim_review",
            "mart.dim_author",
            "mart.dim_workflow_type",
            "mart.dim_status",
            "mart.fact_approval_event",
            "mart.fact_request_lifecycle",
            "mart.fact_reminder",
            "mart.fact_dashboard_snapshot",
        ]:
            self.assertIn(table, mart_sql)

    def test_views_procs_and_indexes_are_declared(self) -> None:
        reporting_sql = (SQL_DIR / "06_views_and_procs.sql").read_text(encoding="utf-8").casefold()
        index_sql = (SQL_DIR / "07_indexes_security_backup_notes.sql").read_text(encoding="utf-8").casefold()

        self.assertIn("create or alter view rpt.vw_open_approval_queue", reporting_sql)
        self.assertIn("create or alter procedure rpt.usp_request_lifecycle_summary", reporting_sql)
        self.assertIn("create nonclustered index", index_sql)
        self.assertIn("create role research_ops_reader", index_sql)


if __name__ == "__main__":
    unittest.main()

