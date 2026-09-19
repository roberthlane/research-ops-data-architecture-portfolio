from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from research_ops_architecture.quality import run_quality_checks
from research_ops_architecture.sqlite_mirror import (
    connect_mirror,
    load_synthetic_csvs,
    run_core_and_mart_load,
)
from research_ops_architecture.synthetic import build_synthetic_dataset


class PipelineTests(unittest.TestCase):
    def test_synthetic_dataset_loads_and_passes_quality_checks(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dataset = build_synthetic_dataset(tmp)
            conn = connect_mirror()
            load_synthetic_csvs(conn, dataset.output_dir)
            run_core_and_mart_load(conn)

            results = run_quality_checks(conn)

        self.assertTrue(all(result.passed for result in results), results)

    def test_generated_dataset_contains_expected_tables(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dataset = build_synthetic_dataset(tmp)

            self.assertGreaterEqual(dataset.row_counts["requests"], 10)
            self.assertGreater(dataset.row_counts["authors"], dataset.row_counts["requests"])
            self.assertGreater(dataset.row_counts["approval_events"], dataset.row_counts["requests"])

    def test_synthetic_data_does_not_include_private_identifiers(self) -> None:
        private_terms = ["@", "https://", "http://", "token", "CD120"]
        with tempfile.TemporaryDirectory() as tmp:
            build_synthetic_dataset(tmp)
            text = "\n".join(path.read_text(encoding="utf-8") for path in Path(tmp).glob("*.csv"))

        self.assertIn("SYN-REVIEW-0001", text)
        self.assertIn("Demo Author 01", text)
        for term in private_terms:
            self.assertNotIn(term, text)

    def test_lifecycle_fact_matches_request_count(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            build_synthetic_dataset(tmp)
            conn = connect_mirror()
            load_synthetic_csvs(conn, tmp)
            run_core_and_mart_load(conn)

            request_count = conn.execute("SELECT COUNT(*) FROM core_request").fetchone()[0]
            fact_count = conn.execute("SELECT COUNT(*) FROM mart_fact_request_lifecycle").fetchone()[0]

        self.assertEqual(fact_count, request_count)


if __name__ == "__main__":
    unittest.main()

