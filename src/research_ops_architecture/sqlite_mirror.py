from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from .models import TABLES


class InputDataError(ValueError):
    """A safe table identifier and reason; never a raw path or cell value."""

    def __init__(self, table: str, reason: str) -> None:
        self.table = table
        self.reason = reason
        super().__init__(f"{table}: {reason}")


def connect_mirror() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    create_schema(conn)
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    for spec in TABLES.values():
        columns = ", ".join(f"{column} TEXT" for column in spec.columns)
        conn.execute(f"CREATE TABLE stg_{spec.name} ({columns})")
    conn.executescript(
        """
        CREATE TABLE core_request (
            request_id TEXT PRIMARY KEY,
            workflow_type TEXT NOT NULL,
            review_title TEXT NOT NULL,
            review_identifier TEXT NOT NULL UNIQUE,
            contact_author_name TEXT NOT NULL,
            created_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            current_status TEXT NOT NULL,
            completion_date TEXT,
            dashboard_export_status TEXT NOT NULL
        );

        CREATE TABLE core_author_approval (
            author_approval_id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL REFERENCES core_request(request_id),
            author_name TEXT NOT NULL,
            author_role TEXT NOT NULL,
            display_order INTEGER NOT NULL,
            approval_status TEXT NOT NULL,
            date_sent TEXT,
            date_approved TEXT,
            last_reminder_sent TEXT,
            reminder_due TEXT
        );

        CREATE TABLE core_approval_event (
            event_id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL REFERENCES core_request(request_id),
            author_approval_id TEXT REFERENCES core_author_approval(author_approval_id),
            event_type TEXT NOT NULL,
            event_timestamp TEXT NOT NULL,
            actor_role TEXT NOT NULL,
            approval_method TEXT,
            comments TEXT
        );

        CREATE TABLE mart_dim_status (
            status_key INTEGER PRIMARY KEY,
            status_code TEXT NOT NULL UNIQUE
        );

        CREATE TABLE mart_dim_author (
            author_key INTEGER PRIMARY KEY,
            author_approval_id TEXT NOT NULL,
            author_name TEXT NOT NULL,
            author_role TEXT NOT NULL,
            approval_status TEXT NOT NULL,
            effective_start_date TEXT NOT NULL,
            effective_end_date TEXT,
            is_current INTEGER NOT NULL,
            UNIQUE(author_approval_id, effective_start_date)
        );

        CREATE TABLE mart_fact_request_lifecycle (
            request_id TEXT PRIMARY KEY,
            review_identifier TEXT NOT NULL,
            workflow_type TEXT NOT NULL,
            current_status TEXT NOT NULL,
            created_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            completion_date TEXT,
            cycle_time_days INTEGER,
            total_authors INTEGER NOT NULL,
            approved_authors INTEGER NOT NULL,
            outstanding_authors INTEGER NOT NULL
        );
        """
    )


def load_synthetic_csvs(conn: sqlite3.Connection, data_dir: str | Path) -> None:
    data_path = Path(data_dir)
    for table_name, spec in TABLES.items():
        staging_name = f"stg_{table_name}"
        try:
            with (data_path / f"{table_name}.csv").open(newline="", encoding="utf-8") as handle:
                reader = csv.DictReader(handle, strict=True)
                if reader.fieldnames != list(spec.columns):
                    raise InputDataError(table_name, "CSV columns do not match the contract")
                rows = list(reader)
                if any(None in row or any(value is None for value in row.values()) for row in rows):
                    raise InputDataError(table_name, "CSV row width does not match the header")
        except FileNotFoundError:
            raise InputDataError(table_name, "CSV file is missing") from None
        except UnicodeError:
            raise InputDataError(table_name, "CSV is not valid UTF-8") from None
        except csv.Error:
            raise InputDataError(table_name, "CSV syntax is invalid") from None
        except OSError:
            raise InputDataError(table_name, "CSV file could not be read") from None
        placeholders = ", ".join("?" for _ in spec.columns)
        column_sql = ", ".join(spec.columns)
        conn.executemany(
            f"INSERT INTO {staging_name} ({column_sql}) VALUES ({placeholders})",
            [[row[column] or None for column in spec.columns] for row in rows],
        )
    conn.commit()


def run_core_and_mart_load(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        INSERT INTO core_request (request_id, workflow_type, review_title, review_identifier, contact_author_name, created_date, due_date, current_status, completion_date, dashboard_export_status)
        SELECT request_id, workflow_type, review_title, review_identifier, contact_author_name, created_date, due_date, current_status, completion_date, dashboard_export_status FROM stg_requests;

        INSERT INTO core_author_approval (author_approval_id, request_id, author_name, author_role, display_order, approval_status, date_sent, date_approved, last_reminder_sent, reminder_due)
        SELECT author_approval_id, request_id, author_name, author_role, display_order, approval_status, date_sent, date_approved, last_reminder_sent, reminder_due FROM stg_authors;

        INSERT INTO core_approval_event (event_id, request_id, author_approval_id, event_type, event_timestamp, actor_role, approval_method, comments)
        SELECT event_id, request_id, author_approval_id, event_type, event_timestamp, actor_role, approval_method, comments FROM stg_approval_events;

        INSERT INTO mart_dim_status(status_key, status_code)
        SELECT ROW_NUMBER() OVER (ORDER BY current_status), current_status
        FROM (SELECT DISTINCT current_status FROM core_request);

        INSERT INTO mart_dim_author (
            author_approval_id,
            author_name,
            author_role,
            approval_status,
            effective_start_date,
            effective_end_date,
            is_current
        )
        SELECT
            author_approval_id,
            author_name,
            author_role,
            approval_status,
            COALESCE(date_sent, DATE('now')),
            NULL,
            1
        FROM core_author_approval;

        INSERT INTO mart_fact_request_lifecycle (
            request_id,
            review_identifier,
            workflow_type,
            current_status,
            created_date,
            due_date,
            completion_date,
            cycle_time_days,
            total_authors,
            approved_authors,
            outstanding_authors
        )
        SELECT
            r.request_id,
            r.review_identifier,
            r.workflow_type,
            r.current_status,
            r.created_date,
            r.due_date,
            r.completion_date,
            CASE
                WHEN r.completion_date IS NULL THEN NULL
                ELSE CAST(JULIANDAY(r.completion_date) - JULIANDAY(r.created_date) AS INTEGER)
            END,
            COUNT(a.author_approval_id),
            SUM(CASE WHEN a.approval_status = 'approved' THEN 1 ELSE 0 END),
            SUM(CASE WHEN a.author_approval_id IS NOT NULL AND a.approval_status <> 'approved' THEN 1 ELSE 0 END)
        FROM core_request r
        LEFT JOIN core_author_approval a ON a.request_id = r.request_id
        GROUP BY r.request_id;
        """
    )
    conn.commit()
