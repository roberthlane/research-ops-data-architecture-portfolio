from __future__ import annotations

import sqlite3
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime

from .models import (
    AUTHOR_APPROVAL_STATUSES,
    DATE_COLUMNS,
    INTEGER_COLUMNS,
    OPTIONAL_COLUMNS,
    REFERENCE_DATE,
    REQUEST_STATUSES,
    TABLES,
    VALID_REQUEST_TRANSITIONS,
    WORKFLOW_TYPES,
)

Row = dict[str, str | None]


@dataclass(frozen=True)
class QualityResult:
    name: str
    passed: bool
    detail: str


class DataQualityError(ValueError):
    """One or more data-contract checks failed."""


def require_quality(results: list[QualityResult]) -> None:
    failed = [r for r in results if not r.passed]
    if failed:
        raise DataQualityError("; ".join(f"{r.name}: {r.detail}" for r in failed))


def _rows(conn: sqlite3.Connection, table: str) -> list[Row]:
    return [
        {key: str(row[key]) if row[key] is not None else None for key in row.keys()}
        for row in conn.execute(f"SELECT * FROM {table}")
    ]


def _result(name: str, problems: list[str]) -> QualityResult:
    detail = f"{len(problems)} violations"
    if problems:
        detail += "; " + "; ".join(problems[:5])
    return QualityResult(name, not problems, detail)


def _day(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def run_staging_checks(conn: sqlite3.Connection, today: date | None = None) -> list[QualityResult]:
    today = today or REFERENCE_DATE
    data = {table: _rows(conn, f"stg_{table}") for table in TABLES}
    issues: dict[str, list[str]] = {
        name: []
        for name in (
            "natural keys are present and unique",
            "required fields and values are valid",
            "references resolve within requests",
            "controlled vocabularies are valid",
            "request lifecycle paths match current status",
            "contact authors and aggregate states agree",
            "lifecycle chronology is consistent",
            "dashboard summaries match source records",
            "dashboard exports are current",
        )
    }
    keys, fields, refs, vocab, paths, contacts, chronology, summaries, freshness = issues.values()
    for table, rows in data.items():
        key = TABLES[table].columns[0]
        counts = Counter(row[key] for row in rows)
        if None in counts or any(count > 1 for count in counts.values()):
            keys.append(f"{table}: missing or duplicate key")
        for index, row in enumerate(rows, start=1):
            label = f"{table} row {index}"
            for column, value in row.items():
                if not value and column not in OPTIONAL_COLUMNS[table]:
                    fields.append(f"{label}: missing {column}")
                if value and column in DATE_COLUMNS[table]:
                    try:
                        if column in {"event_timestamp", "last_exported_at"}:
                            parsed = datetime.fromisoformat(value)
                            if len(value) != 19 or parsed.tzinfo is not None:
                                raise ValueError
                        else:
                            if date.fromisoformat(value).isoformat() != value:
                                raise ValueError
                    except ValueError:
                        fields.append(f"{label}: invalid {column}")
                if value and column in INTEGER_COLUMNS.get(table, set()):
                    minimum = 1 if column in {"display_order", "reminder_number"} else 0
                    if (
                        not value.isascii()
                        or not value.isdecimal()
                        or len(value) > 10
                        or not minimum <= int(value) <= 2_147_483_647
                    ):
                        fields.append(f"{label}: invalid {column}")
    if not data["requests"]:
        fields.append("requests: at least one request is required")
    if len({r["review_identifier"] for r in data["requests"]}) != len(data["requests"]):
        keys.append("requests: duplicate review identifier")
    requests = {r["request_id"]: r for r in data["requests"]}
    authors = {r["author_approval_id"]: r for r in data["authors"]}
    for table in (
        "authors",
        "approval_events",
        "reminder_events",
        "generated_documents",
        "dashboard_exports",
    ):
        for row in data[table]:
            if row["request_id"] not in requests:
                refs.append(f"{table}: missing parent request")
            aid = row.get("author_approval_id")
            if aid and (aid not in authors or authors[aid]["request_id"] != row["request_id"]):
                refs.append(f"{table}: author must belong to the same request")
    for table, column, allowed in (
        ("requests", "current_status", REQUEST_STATUSES),
        ("dashboard_exports", "current_status", REQUEST_STATUSES),
        ("authors", "approval_status", AUTHOR_APPROVAL_STATUSES),
        ("authors", "author_role", ("contact author", "co-author")),
        *(
            (table, "workflow_type", WORKFLOW_TYPES)
            for table in ("requests", "generated_documents", "dashboard_exports")
        ),
    ):
        if any(row[column] not in allowed for row in data[table]):
            vocab.append(f"{table}: invalid {column}")
    for event in data["approval_events"]:
        allowed = (
            ("author-sent", "author-approved") if event["author_approval_id"] else REQUEST_STATUSES
        )
        if event["event_type"] not in allowed:
            vocab.append("approval_events: invalid event type")
    for request_id, request in requests.items():
        aa = [a for a in data["authors"] if a["request_id"] == request_id]
        ee = sorted(
            (
                e
                for e in data["approval_events"]
                if e["request_id"] == request_id and not e["author_approval_id"]
            ),
            key=lambda e: e["event_timestamp"] or "",
        )
        states = [e["event_type"] or "" for e in ee]
        if (
            not states
            or states[0] != "draft"
            or states[-1] != request["current_status"]
            or any(
                b not in VALID_REQUEST_TRANSITIONS.get(a, set()) for a, b in zip(states, states[1:])
            )
        ):
            paths.append(f"{request_id}: invalid path or current state")
        contact = [a for a in aa if a["author_role"] == "contact author"]
        if len(contact) != 1 or contact[0]["author_name"] != request["contact_author_name"]:
            contacts.append(f"{request_id}: contact author mismatch")
        approved = sum(a["approval_status"] == "approved" for a in aa)
        status = request["current_status"]
        if (
            (status in {"draft", "ready-to-send", "sent"} and approved)
            or (status == "partially-approved" and not 0 < approved < len(aa))
            or (
                status in {"approved", "generated", "submitted", "archived"}
                and (not aa or approved != len(aa))
            )
        ):
            contacts.append(f"{request_id}: state disagrees with approvals")
        created, due, done = (
            _day(request[c]) for c in ("created_date", "due_date", "completion_date")
        )
        if status in {"generated", "submitted", "archived"} and done is None:
            fields.append(f"{request_id}: completion date required")
        if created and ((due and due < created) or (done and done < created)):
            chronology.append(f"{request_id}: request dates out of order")
        approval_days = [_day(a["date_approved"]) for a in aa]
        last_approval = max((day for day in approval_days if day is not None), default=None)
        for e in ee:
            when = _day(e["event_timestamp"])
            if when and created and when < created:
                chronology.append(f"{request_id}: event precedes creation")
            if (
                e["event_type"] in {"approved", "generated", "submitted"}
                and when
                and last_approval
                and when < last_approval
            ):
                chronology.append(f"{request_id}: event precedes final author approval")
        completed_events = [_day(e["event_timestamp"]) for e in ee if e["event_type"] == status]
        if (
            status in {"generated", "submitted", "archived"}
            and completed_events
            and done != completed_events[-1]
        ):
            chronology.append(f"{request_id}: completion does not match final event")
        for a in aa:
            sent, accepted = _day(a["date_sent"]), _day(a["date_approved"])
            if (a["approval_status"] == "approved") != (accepted is not None) or (
                a["approval_status"] in {"sent", "approved", "needs-follow-up", "declined"}
                and not sent
            ):
                fields.append(f"{request_id}: author state/date mismatch")
            if sent and created and sent < created or accepted and (not sent or accepted < sent):
                chronology.append(f"{request_id}: author dates out of order")
            for event_type, expected in [("author-sent", sent), ("author-approved", accepted)]:
                actual = [
                    _day(e["event_timestamp"])
                    for e in data["approval_events"]
                    if e["author_approval_id"] == a["author_approval_id"]
                    and e["event_type"] == event_type
                ]
                if actual != ([expected] if expected else []):
                    chronology.append(f"{request_id}: author event/date mismatch")
        dd = [d for d in data["dashboard_exports"] if d["request_id"] == request_id]
        if len(dd) != 1:
            summaries.append(f"{request_id}: exactly one export required")
        else:
            d = dd[0]
            if [d[c] for c in ("total_authors", "approved_authors", "outstanding_authors")] != [
                str(len(aa)),
                str(approved),
                str(len(aa) - approved),
            ] or any(
                d[c] != request[c]
                for c in ("current_status", "workflow_type", "review_identifier", "review_title")
            ):
                summaries.append(f"{request_id}: export disagrees with source")
        for doc in (d for d in data["generated_documents"] if d["request_id"] == request_id):
            generated = [_day(e["event_timestamp"]) for e in ee if e["event_type"] == "generated"]
            if not generated or _day(doc["generated_at"]) != generated[0]:
                chronology.append(f"{request_id}: document does not match generation event")
    for row in data["dashboard_exports"]:
        exported = _day(row["last_exported_at"])
        if not exported or not 0 <= (today - exported).days <= 2:
            freshness.append("export must be within the reference date's last two calendar days")
    return [_result(name, problems) for name, problems in issues.items()]


def run_mart_checks(conn: sqlite3.Connection) -> list[QualityResult]:
    expected = {
        row[0]: tuple(row[1:])
        for row in conn.execute("""
        SELECT r.request_id, COUNT(a.author_approval_id),
               SUM(CASE WHEN a.approval_status='approved' THEN 1 ELSE 0 END),
               SUM(CASE WHEN a.author_approval_id IS NOT NULL AND a.approval_status<>'approved' THEN 1 ELSE 0 END)
        FROM core_request r LEFT JOIN core_author_approval a ON a.request_id=r.request_id
        GROUP BY r.request_id
    """)
    }
    actual = {
        row[0]: tuple(row[1:])
        for row in conn.execute("""
        SELECT request_id,total_authors,approved_authors,outstanding_authors FROM mart_fact_request_lifecycle
    """)
    }
    return [
        QualityResult(
            "mart lifecycle facts match core",
            actual == expected,
            f"{len(actual)}/{len(expected)} requests; counts {'match' if actual == expected else 'differ'}",
        )
    ]


def run_quality_checks(conn: sqlite3.Connection, today: date | None = None) -> list[QualityResult]:
    return run_staging_checks(conn, today) + run_mart_checks(conn)


def render_quality_report(results: list[QualityResult]) -> str:
    return "# Data Quality Report\n\n" + "".join(
        f"- {'PASS' if r.passed else 'FAIL'}: {r.name} - {r.detail}\n" for r in results
    )
