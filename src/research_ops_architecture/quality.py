from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import date, datetime

from .models import VALID_REQUEST_TRANSITIONS


@dataclass(frozen=True)
class QualityResult:
    name: str
    passed: bool
    detail: str


def run_quality_checks(conn: sqlite3.Connection, today: date | None = None) -> list[QualityResult]:
    today = today or date(2026, 7, 1)
    checks = [
        _no_duplicate_request_ids(conn),
        _authors_have_requests(conn),
        _events_have_requests(conn),
        _valid_status_transitions(conn),
        _required_dates_present(conn),
        _dashboard_exports_not_stale(conn, today=today),
        _mart_counts_match_core(conn),
    ]
    return checks


def assert_quality(conn: sqlite3.Connection, today: date | None = None) -> None:
    failed = [check for check in run_quality_checks(conn, today=today) if not check.passed]
    if failed:
        details = "\n".join(f"{check.name}: {check.detail}" for check in failed)
        raise AssertionError(details)


def render_quality_report(results: list[QualityResult]) -> str:
    lines = ["# Data Quality Report", ""]
    for result in results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"- {status}: {result.name} - {result.detail}")
    lines.append("")
    return "\n".join(lines)


def _no_duplicate_request_ids(conn: sqlite3.Connection) -> QualityResult:
    duplicates = conn.execute(
        """
        SELECT request_id, COUNT(*) AS row_count
        FROM stg_requests
        GROUP BY request_id
        HAVING COUNT(*) > 1
        """
    ).fetchall()
    return QualityResult("no duplicate request natural keys", not duplicates, f"{len(duplicates)} duplicates")


def _authors_have_requests(conn: sqlite3.Connection) -> QualityResult:
    missing = conn.execute(
        """
        SELECT COUNT(*) AS missing_count
        FROM stg_authors a
        LEFT JOIN stg_requests r ON r.request_id = a.request_id
        WHERE r.request_id IS NULL
        """
    ).fetchone()["missing_count"]
    return QualityResult("authors reference existing requests", missing == 0, f"{missing} missing parents")


def _events_have_requests(conn: sqlite3.Connection) -> QualityResult:
    missing = conn.execute(
        """
        SELECT COUNT(*) AS missing_count
        FROM stg_approval_events e
        LEFT JOIN stg_requests r ON r.request_id = e.request_id
        WHERE r.request_id IS NULL
        """
    ).fetchone()["missing_count"]
    return QualityResult("events reference existing requests", missing == 0, f"{missing} missing parents")


def _valid_status_transitions(conn: sqlite3.Connection) -> QualityResult:
    rows = conn.execute(
        """
        SELECT request_id, event_type, event_timestamp
        FROM stg_approval_events
        WHERE author_approval_id IS NULL
        ORDER BY request_id, event_timestamp
        """
    ).fetchall()
    invalid: list[str] = []
    prior_by_request: dict[str, str] = {}
    for row in rows:
        request_id = row["request_id"]
        event_type = row["event_type"]
        prior = prior_by_request.get(request_id)
        if prior and event_type not in VALID_REQUEST_TRANSITIONS.get(prior, set()):
            invalid.append(f"{request_id}: {prior}->{event_type}")
        prior_by_request[request_id] = event_type
    return QualityResult("request status transitions are valid", not invalid, f"{len(invalid)} invalid transitions")


def _required_dates_present(conn: sqlite3.Connection) -> QualityResult:
    missing = conn.execute(
        """
        SELECT COUNT(*) AS missing_count
        FROM stg_requests
        WHERE created_date IS NULL
           OR due_date IS NULL
           OR (current_status IN ('generated', 'submitted', 'archived') AND completion_date IS NULL)
        """
    ).fetchone()["missing_count"]
    return QualityResult("required lifecycle dates are present", missing == 0, f"{missing} incomplete rows")


def _dashboard_exports_not_stale(conn: sqlite3.Connection, today: date) -> QualityResult:
    rows = conn.execute("SELECT request_id, last_exported_at FROM stg_dashboard_exports").fetchall()
    stale = []
    for row in rows:
        exported = datetime.fromisoformat(row["last_exported_at"]).date()
        if (today - exported).days > 2:
            stale.append(row["request_id"])
    return QualityResult("dashboard exports are current", not stale, f"{len(stale)} stale exports")


def _mart_counts_match_core(conn: sqlite3.Connection) -> QualityResult:
    core_count = conn.execute("SELECT COUNT(*) FROM core_request").fetchone()[0]
    fact_count = conn.execute("SELECT COUNT(*) FROM mart_fact_request_lifecycle").fetchone()[0]
    return QualityResult("mart lifecycle fact count matches core requests", core_count == fact_count, f"{fact_count}/{core_count}")

