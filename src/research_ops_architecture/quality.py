from __future__ import annotations

import sqlite3
from collections import Counter, defaultdict
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
Groups = dict[str | None, list[Row]]


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


def _group(rows: list[Row], column: str) -> Groups:
    groups: Groups = defaultdict(list)
    for row in rows:
        groups[row[column]].append(row)
    return groups


@dataclass
class StagingData:
    """One read and grouping pass; checks never rescan an unrelated request's rows."""

    tables: dict[str, list[Row]]
    requests: dict[str | None, Row]
    authors: dict[str | None, Row]
    authors_by_request: Groups
    request_events: Groups
    author_events: dict[tuple[str | None, str | None], list[Row]]
    exports: Groups
    documents: Groups

    @classmethod
    def read(cls, conn: sqlite3.Connection) -> StagingData:
        tables = {table: _rows(conn, f"stg_{table}") for table in TABLES}
        request_events: Groups = defaultdict(list)
        author_events: dict[tuple[str | None, str | None], list[Row]] = defaultdict(list)
        for event in tables["approval_events"]:
            if event["author_approval_id"]:
                author_events[event["author_approval_id"], event["event_type"]].append(event)
            else:
                request_events[event["request_id"]].append(event)
        for events in request_events.values():
            events.sort(key=lambda e: e["event_timestamp"] or "")
        return cls(
            tables=tables,
            requests={r["request_id"]: r for r in tables["requests"]},
            authors={r["author_approval_id"]: r for r in tables["authors"]},
            authors_by_request=_group(tables["authors"], "request_id"),
            request_events=request_events,
            author_events=author_events,
            exports=_group(tables["dashboard_exports"], "request_id"),
            documents=_group(tables["generated_documents"], "request_id"),
        )


def _result(name: str, problems: list[str]) -> QualityResult:
    # Each message represents one rule violation, not a distinct affected row.
    detail = f"{len(problems)} {'violation' if len(problems) == 1 else 'violations'}"
    if problems:
        detail += "; " + "; ".join(problems[:5])
    if len(problems) > 5:
        detail += "; showing first 5"
    return QualityResult(name, not problems, detail)


def _day(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value).date()
    except ValueError:
        return None


def _check_keys(data: StagingData) -> QualityResult:
    problems: list[str] = []
    for table, rows in data.tables.items():
        key = TABLES[table].columns[0]
        counts = Counter(row[key] for row in rows)
        for index, row in enumerate(rows, 1):
            if not row[key]:
                problems.append(f"{table} row {index}: missing key")
            elif counts[row[key]] > 1:
                problems.append(f"{table} row {index}: duplicate key")
    reviews = Counter(r["review_identifier"] for r in data.tables["requests"])
    for index, request in enumerate(data.tables["requests"], 1):
        if request["review_identifier"] and reviews[request["review_identifier"]] > 1:
            problems.append(f"requests row {index}: duplicate review identifier")
    return _result("natural keys are present and unique", problems)


def _check_fields(data: StagingData) -> QualityResult:
    problems: list[str] = []
    for table, rows in data.tables.items():
        for index, row in enumerate(rows, 1):
            label = f"{table} row {index}"
            for column, value in row.items():
                if not value and column not in OPTIONAL_COLUMNS[table]:
                    problems.append(f"{label}: missing {column}")
                if value and column in DATE_COLUMNS[table]:
                    try:
                        if column in {"event_timestamp", "last_exported_at"}:
                            parsed = datetime.fromisoformat(value)
                            if len(value) != 19 or parsed.tzinfo is not None:
                                raise ValueError
                        elif date.fromisoformat(value).isoformat() != value:
                            raise ValueError
                    except ValueError:
                        problems.append(f"{label}: invalid {column}")
                if value and column in INTEGER_COLUMNS.get(table, set()):
                    minimum = 1 if column in {"display_order", "reminder_number"} else 0
                    if (
                        not value.isascii()
                        or not value.isdecimal()
                        or len(value) > 10
                        or not minimum <= int(value) <= 2_147_483_647
                    ):
                        problems.append(f"{label}: invalid {column}")
    if not data.tables["requests"]:
        problems.append("requests: at least one request is required")
    for index, request in enumerate(data.tables["requests"], 1):
        if request["current_status"] in {"generated", "submitted", "archived"} and not _day(
            request["completion_date"]
        ):
            problems.append(f"requests row {index}: completion date required")
    for index, author in enumerate(data.tables["authors"], 1):
        sent, accepted = _day(author["date_sent"]), _day(author["date_approved"])
        if (author["approval_status"] == "approved") != (accepted is not None):
            problems.append(f"authors row {index}: approval state/date mismatch")
        if (
            author["approval_status"] in {"sent", "approved", "needs-follow-up", "declined"}
            and not sent
        ):
            problems.append(f"authors row {index}: send date required")
    return _result("required fields and values are valid", problems)


def _check_references(data: StagingData) -> QualityResult:
    problems: list[str] = []
    for table in (
        "authors",
        "approval_events",
        "reminder_events",
        "generated_documents",
        "dashboard_exports",
    ):
        for index, row in enumerate(data.tables[table], 1):
            parent = data.requests.get(row["request_id"])
            if parent is None:
                problems.append(f"{table} row {index}: missing parent request")
            aid = row.get("author_approval_id")
            if aid and (
                aid not in data.authors or data.authors[aid]["request_id"] != row["request_id"]
            ):
                problems.append(f"{table} row {index}: author must belong to the same request")
            if (
                table == "generated_documents"
                and parent
                and row["workflow_type"] != parent["workflow_type"]
            ):
                problems.append(f"{table} row {index}: workflow must match parent request")
    review_ids = {r["review_identifier"] for r in data.tables["requests"] if r["review_identifier"]}
    for index, project in enumerate(data.tables["project_status"], 1):
        if project["review_identifier"] not in review_ids:
            problems.append(f"project_status row {index}: missing parent review")
    return _result("references resolve within requests", problems)


def _check_vocabularies(data: StagingData) -> QualityResult:
    problems: list[str] = []
    contracts = [
        ("requests", "current_status", REQUEST_STATUSES),
        ("dashboard_exports", "current_status", REQUEST_STATUSES),
        ("authors", "approval_status", AUTHOR_APPROVAL_STATUSES),
        ("authors", "author_role", ("contact author", "co-author")),
        *(
            (table, "workflow_type", WORKFLOW_TYPES)
            for table in ("requests", "generated_documents", "dashboard_exports")
        ),
    ]
    for table, column, allowed in contracts:
        for index, row in enumerate(data.tables[table], 1):
            if row[column] not in allowed:
                problems.append(f"{table} row {index}: invalid {column}")
    for index, event in enumerate(data.tables["approval_events"], 1):
        allowed = (
            ("author-sent", "author-approved") if event["author_approval_id"] else REQUEST_STATUSES
        )
        if event["event_type"] not in allowed:
            problems.append(f"approval_events row {index}: invalid event type")
    return _result("controlled vocabularies are valid", problems)


def _check_paths(data: StagingData) -> QualityResult:
    problems: list[str] = []
    for rid, request in data.requests.items():
        states = [e["event_type"] or "" for e in data.request_events.get(rid, [])]
        if (
            not states
            or states[0] != "draft"
            or states[-1] != request["current_status"]
            or any(
                b not in VALID_REQUEST_TRANSITIONS.get(a, set()) for a, b in zip(states, states[1:])
            )
        ):
            problems.append(f"{rid}: invalid path or current state")
    return _result("request lifecycle paths match current status", problems)


def _check_contacts(data: StagingData) -> QualityResult:
    problems: list[str] = []
    for rid, request in data.requests.items():
        authors = data.authors_by_request.get(rid, [])
        contacts = [a for a in authors if a["author_role"] == "contact author"]
        if len(contacts) != 1 or contacts[0]["author_name"] != request["contact_author_name"]:
            problems.append(f"{rid}: contact author mismatch")
        approved = sum(a["approval_status"] == "approved" for a in authors)
        status = request["current_status"]
        if (
            (status in {"draft", "ready-to-send", "sent"} and approved)
            or (status == "partially-approved" and not 0 < approved < len(authors))
            or (
                status in {"approved", "generated", "submitted", "archived"}
                and (not authors or approved != len(authors))
            )
        ):
            problems.append(f"{rid}: state disagrees with approvals")
    return _result("contact authors and aggregate states agree", problems)


def _author_chronology(data: StagingData, author: Row, created: date | None) -> list[str]:
    problems: list[str] = []
    rid = author["request_id"]
    sent, accepted = _day(author["date_sent"]), _day(author["date_approved"])
    if (sent and created and sent < created) or (accepted and (not sent or accepted < sent)):
        problems.append(f"{rid}: author dates out of order")
    for event_type, expected in [("author-sent", sent), ("author-approved", accepted)]:
        events = data.author_events.get((author["author_approval_id"], event_type), [])
        if [_day(e["event_timestamp"]) for e in events] != ([expected] if expected else []):
            problems.append(f"{rid}: author event/date mismatch")
    return problems


def _check_chronology(data: StagingData) -> QualityResult:
    problems: list[str] = []
    for rid, request in data.requests.items():
        events = data.request_events.get(rid, [])
        authors = data.authors_by_request.get(rid, [])
        created, due, done = (
            _day(request[c]) for c in ("created_date", "due_date", "completion_date")
        )
        if created and ((due and due < created) or (done and done < created)):
            problems.append(f"{rid}: request dates out of order")
        last_approval = max(
            (day for a in authors if (day := _day(a["date_approved"])) is not None), default=None
        )
        for event in events:
            when = _day(event["event_timestamp"])
            if when and created and when < created:
                problems.append(f"{rid}: event precedes creation")
            if (
                event["event_type"] in {"approved", "generated", "submitted"}
                and when
                and last_approval
                and when < last_approval
            ):
                problems.append(f"{rid}: event precedes final author approval")
        completed = [
            _day(e["event_timestamp"])
            for e in events
            if e["event_type"] == request["current_status"]
        ]
        if (
            request["current_status"] in {"generated", "submitted", "archived"}
            and completed
            and done != completed[-1]
        ):
            problems.append(f"{rid}: completion does not match final event")
        for author in authors:
            problems.extend(_author_chronology(data, author, created))
        generated = [_day(e["event_timestamp"]) for e in events if e["event_type"] == "generated"]
        for doc in data.documents.get(rid, []):
            if not generated or _day(doc["generated_at"]) != generated[0]:
                problems.append(f"{rid}: document does not match generation event")
    return _result("lifecycle chronology is consistent", problems)


def _check_summaries(data: StagingData) -> QualityResult:
    problems: list[str] = []
    for rid, request in data.requests.items():
        exports = data.exports.get(rid, [])
        if len(exports) != 1:
            problems.append(f"{rid}: exactly one export required")
            continue
        authors = data.authors_by_request.get(rid, [])
        approved = sum(a["approval_status"] == "approved" for a in authors)
        export = exports[0]
        if [export[c] for c in ("total_authors", "approved_authors", "outstanding_authors")] != [
            str(len(authors)),
            str(approved),
            str(len(authors) - approved),
        ] or any(
            export[c] != request[c]
            for c in ("current_status", "workflow_type", "review_identifier", "review_title")
        ):
            problems.append(f"{rid}: export disagrees with source")
    return _result("dashboard summaries match source records", problems)


def _check_freshness(data: StagingData, today: date) -> QualityResult:
    problems: list[str] = []
    for index, row in enumerate(data.tables["dashboard_exports"], 1):
        exported = _day(row["last_exported_at"])
        if not exported or not 0 <= (today - exported).days <= 2:
            problems.append(
                f"dashboard_exports row {index}: export must be within the reference date's last two calendar days"
            )
    return _result("dashboard exports are current", problems)


def run_staging_checks(conn: sqlite3.Connection, today: date | None = None) -> list[QualityResult]:
    data = StagingData.read(conn)
    return [
        _check_keys(data),
        _check_fields(data),
        _check_references(data),
        _check_vocabularies(data),
        _check_paths(data),
        _check_contacts(data),
        _check_chronology(data),
        _check_summaries(data),
        _check_freshness(data, today or REFERENCE_DATE),
    ]


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
