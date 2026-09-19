from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from .models import TABLES


def connect_mirror() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    create_schema(conn)
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE stg_requests (
            request_id TEXT PRIMARY KEY,
            workflow_type TEXT NOT NULL,
            review_title TEXT NOT NULL,
            review_identifier TEXT NOT NULL,
            contact_author_name TEXT NOT NULL,
            created_date TEXT NOT NULL,
            due_date TEXT NOT NULL,
            current_status TEXT NOT NULL,
            completion_date TEXT,
            dashboard_export_status TEXT NOT NULL
        );

        CREATE TABLE stg_authors (
            author_approval_id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL,
            author_name TEXT NOT NULL,
            author_role TEXT NOT NULL,
            display_order INTEGER NOT NULL,
            approval_status TEXT NOT NULL,
            date_sent TEXT,
            date_approved TEXT,
            last_reminder_sent TEXT,
            reminder_due TEXT
        );

        CREATE TABLE stg_approval_events (
            event_id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL,
            author_approval_id TEXT,
            event_type TEXT NOT NULL,
            event_timestamp TEXT NOT NULL,
            actor_role TEXT NOT NULL,
            approval_method TEXT,
            comments TEXT
        );

        CREATE TABLE stg_reminder_events (
            reminder_id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL,
            author_approval_id TEXT NOT NULL,
            reminder_type TEXT NOT NULL,
            sent_at TEXT,
            sent_by TEXT NOT NULL,
            reminder_number INTEGER NOT NULL,
            delivery_status TEXT NOT NULL,
            next_reminder_due TEXT
        );

        CREATE TABLE stg_generated_documents (
            document_id TEXT PRIMARY KEY,
            request_id TEXT NOT NULL,
            workflow_type TEXT NOT NULL,
            template_version TEXT NOT NULL,
            generated_at TEXT NOT NULL,
            generated_by TEXT NOT NULL,
            document_status TEXT NOT NULL
        );

        CREATE TABLE stg_dashboard_exports (
            request_id TEXT PRIMARY KEY,
            workflow_type TEXT NOT NULL,
            review_title TEXT NOT NULL,
            review_identifier TEXT NOT NULL,
            total_authors INTEGER NOT NULL,
            approved_authors INTEGER NOT NULL,
            outstanding_authors INTEGER NOT NULL,
            current_status TEXT NOT NULL,
            last_reminder_sent TEXT,
            reminder_due TEXT,
            waiting_on TEXT,
            last_exported_at TEXT NOT NULL
        );

        CREATE TABLE stg_project_status (
            review_identifier TEXT PRIMARY KEY,
            review_title TEXT NOT NULL,
            project_phase TEXT NOT NULL,
            priority TEXT NOT NULL,
            owner_role TEXT NOT NULL,
            status_as_of TEXT NOT NULL,
            next_milestone_due TEXT NOT NULL
        );

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
        with (data_path / f"{table_name}.csv").open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = list(reader)
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
        INSERT INTO core_request
        SELECT * FROM stg_requests;

        INSERT INTO core_author_approval
        SELECT * FROM stg_authors;

        INSERT INTO core_approval_event
        SELECT * FROM stg_approval_events;

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
            d.total_authors,
            d.approved_authors,
            d.outstanding_authors
        FROM core_request r
        JOIN stg_dashboard_exports d ON d.request_id = r.request_id;
        """
    )
    conn.commit()

