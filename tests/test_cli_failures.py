from __future__ import annotations

import csv
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from research_ops_architecture.cli import main
from research_ops_architecture.models import TABLES
from research_ops_architecture.quality import run_mart_checks, run_staging_checks
from research_ops_architecture.sqlite_mirror import (
    connect_mirror,
    load_synthetic_csvs,
    run_core_and_mart_load,
)
from research_ops_architecture.synthetic import build_synthetic_dataset

ROOT = Path(__file__).resolve().parents[1]


class CliFailureTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.data = Path(self.temp.name) / "data"
        self.report = Path(self.temp.name) / "report.md"
        build_synthetic_dataset(self.data)

    def rewrite(self, table: str, row_index: int, column: str, value: str) -> None:
        path = self.data / f"{table}.csv"
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        rows[row_index][column] = value
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=TABLES[table].columns)
            writer.writeheader()
            writer.writerows(rows)

    def invoke(self) -> subprocess.CompletedProcess[str]:
        env = dict(os.environ, PYTHONPATH=str(ROOT / "src"), PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run(
            [
                sys.executable,
                "-m",
                "research_ops_architecture.cli",
                "--skip-generate",
                "--data-dir",
                str(self.data),
                "--report",
                str(self.report),
            ],
            cwd=self.temp.name,
            env=env,
            text=True,
            capture_output=True,
        )

    def test_invalid_csv_records_write_fail_report_and_exit_nonzero(self) -> None:
        cases = [
            ("requests", "request_id", "", "natural keys"),
            ("authors", "request_id", "MISSING", "references resolve"),
            ("approval_events", "request_id", "MISSING", "references resolve"),
            ("project_status", "review_identifier", "MISSING", "references resolve"),
            ("generated_documents", "workflow_type", "authorship-change", "references resolve"),
            ("requests", "created_date", "", "required fields"),
            ("requests", "completion_date", "", "required fields"),
            ("requests", "due_date", "not-a-date", "required fields"),
            ("requests", "current_status", "invalid-state", "controlled vocabularies"),
            ("authors", "approval_status", "invalid-state", "controlled vocabularies"),
            ("requests", "contact_author_name", "Wrong placeholder", "contact authors"),
            ("requests", "current_status", "sent", "request states"),
            ("authors", "date_approved", "2020-01-01", "lifecycle chronology"),
            ("authors", "date_approved", "2026-06-01", "lifecycle chronology"),
            ("dashboard_exports", "total_authors", "999", "dashboard summaries"),
            ("dashboard_exports", "total_authors", "-1", "required fields"),
            ("dashboard_exports", "total_authors", "9" * 5000, "required fields"),
            ("dashboard_exports", "last_exported_at", "2026-06-28T00:00:00", "dashboard exports"),
            ("dashboard_exports", "last_exported_at", "2026-07-02T00:00:00", "dashboard exports"),
        ]
        for table, column, value, check in cases:
            with self.subTest(table=table, column=column, value=value):
                build_synthetic_dataset(self.data)
                self.rewrite(table, 0, column, value)
                self.report.write_text("old successful report")
                result = self.invoke()
                self.assertEqual(result.returncode, 1, result.stderr)
                report = self.report.read_text()
                self.assertIn("FAIL:", report)
                self.assertIn(f"FAIL: {check}", report)
                self.assertNotIn("old successful", report)
                self.assertNotIn("Traceback", result.stderr)

    def test_contact_identity_and_approval_state_report_independently(self) -> None:
        cases = [
            (
                "contact_author_name",
                "Wrong placeholder",
                "contact authors match request identity",
                "request states agree with author approvals",
            ),
            (
                "current_status",
                "sent",
                "request states agree with author approvals",
                "contact authors match request identity",
            ),
        ]
        for column, value, failed, passed in cases:
            with self.subTest(column=column):
                build_synthetic_dataset(self.data)
                self.rewrite("requests", 0, column, value)
                self.assertEqual(self.invoke().returncode, 1)
                report = self.report.read_text()
                self.assertIn(f"FAIL: {failed} - 1 violation;", report)
                self.assertIn(f"PASS: {passed} - 0 violations", report)

    def test_duplicates_reach_quality_gate_before_core_loading(self) -> None:
        path = self.data / "requests.csv"
        lines = path.read_text().splitlines()
        path.write_text("\n".join(lines + [lines[1]]) + "\n")
        with patch("research_ops_architecture.cli.run_core_and_mart_load") as core_load:
            result = main(
                ["--skip-generate", "--data-dir", str(self.data), "--report", str(self.report)]
            )
            core_load.assert_not_called()
        self.assertEqual(result, 1)
        self.assertIn("FAIL: natural keys", self.report.read_text())

    def test_broken_headers_missing_files_and_row_width_produce_reports(self) -> None:
        for defect in ("header", "missing", "width", "empty", "encoding"):
            with self.subTest(defect=defect):
                build_synthetic_dataset(self.data)
                path = self.data / "requests.csv"
                if defect == "header":
                    path.write_text("wrong,header\na,b\n")
                elif defect == "missing":
                    path.unlink()
                elif defect == "width":
                    with path.open("a") as handle:
                        handle.write("too,few\n")
                elif defect == "empty":
                    path.write_text(path.read_text().splitlines()[0] + "\n")
                else:
                    path.write_bytes(b"\xff")
                self.assertEqual(self.invoke().returncode, 1)
                self.assertIn("FAIL:", self.report.read_text())

    def test_freshness_calendar_boundary_accepts_two_days(self) -> None:
        self.rewrite("dashboard_exports", 0, "last_exported_at", "2026-06-29T00:00:00")
        self.assertEqual(self.invoke().returncode, 0)

    def test_load_errors_name_table_without_paths_or_input_contents(self) -> None:
        (self.data / "authors.csv").unlink()
        result = self.invoke()
        self.assertEqual(result.returncode, 1)
        self.assertIn("authors: CSV file is missing", self.report.read_text())
        self.assertNotIn(str(self.data), self.report.read_text())
        build_synthetic_dataset(self.data)
        (self.data / "requests.csv").write_text("PRIVATE-HEADER,PRIVATE-VALUE\na,b\n")
        self.assertEqual(self.invoke().returncode, 1)
        report = self.report.read_text()
        self.assertIn("requests: CSV columns do not match the contract", report)
        self.assertNotIn("PRIVATE", report)
        self.assertNotIn(str(self.data), report)

    def test_vocabulary_counts_each_invalid_row_with_singular_grammar(self) -> None:
        for count in (1, 3):
            with self.subTest(count=count):
                build_synthetic_dataset(self.data)
                for index in range(count):
                    self.rewrite("requests", index, "current_status", "bogus")
                self.assertEqual(self.invoke().returncode, 1)
                line = next(
                    line
                    for line in self.report.read_text().splitlines()
                    if line.startswith("- FAIL: controlled vocabularies")
                )
                noun = "violation" if count == 1 else "violations"
                self.assertIn(f" - {count} {noun};", line)

    def test_duplicate_key_count_includes_each_affected_row(self) -> None:
        path = self.data / "requests.csv"
        lines = path.read_text().splitlines()
        # Original row plus two copies: three key and three review-key violations.
        path.write_text("\n".join(lines + [lines[1], lines[1]]) + "\n")
        self.assertEqual(self.invoke().returncode, 1)
        report = self.report.read_text()
        self.assertIn("natural keys are present and unique - 6 violations;", report)
        self.assertIn("showing first 5", report)

    def test_unsorted_events_pass_but_duplicate_author_event_fails(self) -> None:
        path = self.data / "approval_events.csv"
        with path.open(newline="") as handle:
            rows = list(csv.DictReader(handle))
        with path.open("w", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=TABLES["approval_events"].columns)
            writer.writeheader()
            writer.writerows(reversed(rows))
        self.assertEqual(self.invoke().returncode, 0)
        duplicate = next(row.copy() for row in rows if row["event_type"] == "author-approved")
        duplicate["event_id"] = "EXTRA-AUTHOR-APPROVAL"
        with path.open("a", newline="") as handle:
            csv.DictWriter(handle, fieldnames=TABLES["approval_events"].columns).writerow(duplicate)
        self.assertEqual(self.invoke().returncode, 1)
        self.assertIn("FAIL: lifecycle chronology", self.report.read_text())

    def test_event_parent_must_match_author_parent(self) -> None:
        self.rewrite("approval_events", 0, "author_approval_id", "AUT-0002-01")
        self.assertEqual(self.invoke().returncode, 1)
        self.assertIn("FAIL: references resolve", self.report.read_text())

    def test_mart_counts_use_core_even_when_export_is_absent(self) -> None:
        conn = connect_mirror()
        self.addCleanup(conn.close)
        load_synthetic_csvs(conn, self.data)
        conn.execute("DELETE FROM stg_dashboard_exports")
        # Missing exports are a staging error, but they cannot remove facts or supply counts.
        self.assertFalse(all(c.passed for c in run_staging_checks(conn)))
        run_core_and_mart_load(conn)
        self.assertEqual(
            conn.execute("SELECT COUNT(*) FROM mart_fact_request_lifecycle").fetchone()[0], 12
        )
        self.assertTrue(all(c.passed for c in run_mart_checks(conn)))
        conn.execute(
            "UPDATE mart_fact_request_lifecycle SET total_authors=999 WHERE request_id='REQ-0001'"
        )
        self.assertFalse(all(c.passed for c in run_mart_checks(conn)))

    def test_demo_rejects_tampering_with_and_without_optimization(self) -> None:
        copy = Path(self.temp.name) / "copy"
        shutil.copytree(
            ROOT, copy, ignore=shutil.ignore_patterns(".git", "__pycache__", "*.egg-info", "build")
        )
        path = copy / "data/synthetic/requests.csv"
        path.write_text(path.read_text().replace("Synthetic review topic 01", "TAMPERED"))
        env = dict(os.environ, PYTHONPATH=str(copy / "src"), PYTHONDONTWRITEBYTECODE="1")
        for opts in ([], ["-O"]):
            with self.subTest(opts=opts):
                run = subprocess.run(
                    [sys.executable, *opts, "scripts/demo.py"],
                    cwd=copy,
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertNotEqual(run.returncode, 0)
                self.assertIn("Committed fixture differs", run.stderr)
                self.assertNotIn("PASS: 7 committed", run.stdout)

    def test_generated_check_detects_drift_without_overwriting_it(self) -> None:
        copy = Path(self.temp.name) / "copy"
        shutil.copytree(
            ROOT,
            copy,
            ignore=shutil.ignore_patterns(
                ".git",
                "__pycache__",
                "*.egg-info",
                "build",
                ".mypy_cache",
                ".ruff_cache",
            ),
        )
        report = copy / "docs/quality-report.md"
        expected = report.read_bytes()
        report.write_text("deliberate report drift")
        env = dict(os.environ, PYTHONPATH=str(copy / "src"), PYTHONDONTWRITEBYTECODE="1")
        result = subprocess.run(
            [sys.executable, "scripts/check_generated.py"],
            cwd=copy,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Generated artifact differs: docs/quality-report.md", result.stderr)
        self.assertEqual(report.read_text(), "deliberate report drift")
        refreshed = subprocess.run(
            [sys.executable, "scripts/check_generated.py", "--write"],
            cwd=copy,
            env=env,
            capture_output=True,
            text=True,
        )
        self.assertEqual(refreshed.returncode, 0, refreshed.stderr)
        self.assertEqual(report.read_bytes(), expected)
