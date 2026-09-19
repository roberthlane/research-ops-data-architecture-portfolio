from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path

from .models import TABLES, WORKFLOW_TYPES


@dataclass(frozen=True)
class SyntheticDataset:
    output_dir: Path
    row_counts: dict[str, int]


REVIEW_TOPICS = tuple(f"Synthetic review topic {index:02d}" for index in range(1, 13))

AUTHOR_NAMES = tuple(f"Demo Author {index:02d}" for index in range(1, 13))

STATUS_PATHS = (
    ("draft", "ready-to-send", "sent", "partially-approved", "approved", "generated", "submitted"),
    ("draft", "ready-to-send", "sent", "approved", "generated"),
    ("draft", "ready-to-send", "sent", "partially-approved"),
    ("draft", "ready-to-send", "sent"),
    ("draft", "ready-to-send", "cancelled"),
)


def build_synthetic_dataset(output_dir: str | Path, today: date | None = None) -> SyntheticDataset:
    """Write deterministic synthetic research-operations CSVs.

    The data resembles a review approval workflow but contains no private
    review, author, email, token, or document-link data.
    """

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    today = today or date(2026, 7, 1)

    rows = _build_rows(today)
    row_counts = {}
    for table_name, table_rows in rows.items():
        row_counts[table_name] = len(table_rows)
        _write_csv(output_path / f"{table_name}.csv", TABLES[table_name].columns, table_rows)
    return SyntheticDataset(output_dir=output_path, row_counts=row_counts)


def _build_rows(today: date) -> dict[str, list[dict[str, object]]]:
    requests: list[dict[str, object]] = []
    authors: list[dict[str, object]] = []
    approval_events: list[dict[str, object]] = []
    reminder_events: list[dict[str, object]] = []
    generated_documents: list[dict[str, object]] = []
    dashboard_exports: list[dict[str, object]] = []
    project_status: list[dict[str, object]] = []

    for index, title in enumerate(REVIEW_TOPICS, start=1):
        request_id = f"REQ-{index:04d}"
        review_identifier = f"SYN-REVIEW-{index:04d}"
        workflow_type = WORKFLOW_TYPES[index % len(WORKFLOW_TYPES)]
        created = today - timedelta(days=72 - index * 4)
        path = STATUS_PATHS[index % len(STATUS_PATHS)]
        current_status = path[-1]
        completion_date = created + timedelta(days=len(path) * 3) if current_status in {"generated", "submitted"} else ""
        due_date = created + timedelta(days=28)
        total_authors = 3 + (index % 3)
        approved_authors = total_authors if current_status in {"approved", "generated", "submitted"} else max(0, total_authors - 2)
        outstanding_authors = total_authors - approved_authors
        last_reminder = created + timedelta(days=18) if outstanding_authors else ""
        reminder_due = created + timedelta(days=25) if outstanding_authors else ""

        requests.append(
            {
                "request_id": request_id,
                "workflow_type": workflow_type,
                "review_title": title,
                "review_identifier": review_identifier,
                "contact_author_name": AUTHOR_NAMES[index % len(AUTHOR_NAMES)],
                "created_date": created.isoformat(),
                "due_date": due_date.isoformat(),
                "current_status": current_status,
                "completion_date": _iso(completion_date),
                "dashboard_export_status": "exported" if current_status != "draft" else "not-exported",
            }
        )

        for event_number, status in enumerate(path, start=1):
            approval_events.append(
                {
                    "event_id": f"EVT-{index:04d}-{event_number:02d}",
                    "request_id": request_id,
                    "author_approval_id": "",
                    "event_type": status,
                    "event_timestamp": datetime.combine(
                        created + timedelta(days=(event_number - 1) * 3),
                        datetime.min.time(),
                    ).isoformat(timespec="seconds"),
                    "actor_role": "managing-editor" if event_number <= 2 else "author",
                    "approval_method": "checkbox-attestation" if status == "approved" else "",
                    "comments": f"Synthetic lifecycle event {event_number}",
                }
            )

        for author_index in range(1, total_authors + 1):
            author_id = f"AUT-{index:04d}-{author_index:02d}"
            approved = author_index <= approved_authors
            date_sent = created + timedelta(days=8)
            date_approved = created + timedelta(days=12 + author_index) if approved else ""
            author_status = "approved" if approved else ("needs-follow-up" if current_status == "partially-approved" else "sent")
            authors.append(
                {
                    "author_approval_id": author_id,
                    "request_id": request_id,
                    "author_name": AUTHOR_NAMES[(index + author_index) % len(AUTHOR_NAMES)],
                    "author_role": "contact author" if author_index == 1 else "co-author",
                    "display_order": author_index,
                    "approval_status": author_status,
                    "date_sent": date_sent.isoformat(),
                    "date_approved": _iso(date_approved),
                    "last_reminder_sent": _iso(last_reminder),
                    "reminder_due": _iso(reminder_due),
                }
            )
            approval_events.append(
                {
                    "event_id": f"EVT-{index:04d}-A{author_index:02d}",
                    "request_id": request_id,
                    "author_approval_id": author_id,
                    "event_type": "author-approved" if approved else "author-sent",
                    "event_timestamp": datetime.combine(
                        date_approved if approved else date_sent,
                        datetime.min.time(),
                    ).isoformat(timespec="seconds"),
                    "actor_role": "author" if approved else "system",
                    "approval_method": "checkbox-attestation" if approved else "",
                    "comments": "Synthetic author-level event",
                }
            )
            if not approved and current_status not in {"draft", "cancelled"}:
                reminder_events.append(
                    {
                        "reminder_id": f"REM-{index:04d}-{author_index:02d}",
                        "request_id": request_id,
                        "author_approval_id": author_id,
                        "reminder_type": "follow-up",
                        "sent_at": _iso(last_reminder),
                        "sent_by": "workflow-automation",
                        "reminder_number": 1,
                        "delivery_status": "sent",
                        "next_reminder_due": _iso(reminder_due),
                    }
                )

        if current_status in {"generated", "submitted"}:
            generated_at = created + timedelta(days=18)
            generated_documents.append(
                {
                    "document_id": f"DOC-{index:04d}",
                    "request_id": request_id,
                    "workflow_type": workflow_type,
                    "template_version": "2026.07",
                    "generated_at": generated_at.isoformat(),
                    "generated_by": "workflow-automation",
                    "document_status": "final" if current_status == "submitted" else "needs-review",
                }
            )

        dashboard_exports.append(
            {
                "request_id": request_id,
                "workflow_type": workflow_type,
                "review_title": title,
                "review_identifier": review_identifier,
                "total_authors": total_authors,
                "approved_authors": approved_authors,
                "outstanding_authors": outstanding_authors,
                "current_status": current_status,
                "last_reminder_sent": _iso(last_reminder),
                "reminder_due": _iso(reminder_due),
                "waiting_on": "authors" if outstanding_authors else "",
                "last_exported_at": datetime.combine(today, datetime.min.time()).isoformat(timespec="seconds"),
            }
        )
        project_status.append(
            {
                "review_identifier": review_identifier,
                "review_title": title,
                "project_phase": "approval" if current_status not in {"submitted", "archived"} else "submission",
                "priority": "high" if index % 4 == 0 else "normal",
                "owner_role": "managing-editor",
                "status_as_of": today.isoformat(),
                "next_milestone_due": due_date.isoformat(),
            }
        )

    return {
        "requests": requests,
        "authors": authors,
        "approval_events": approval_events,
        "reminder_events": reminder_events,
        "generated_documents": generated_documents,
        "dashboard_exports": dashboard_exports,
        "project_status": project_status,
    }


def _write_csv(path: Path, columns: tuple[str, ...], rows: list[dict[str, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def _iso(value: object) -> str:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value or "")

