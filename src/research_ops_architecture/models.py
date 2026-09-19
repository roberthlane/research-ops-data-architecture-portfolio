from __future__ import annotations

from dataclasses import dataclass
from datetime import date

REFERENCE_DATE = date(2026, 7, 1)


REQUEST_STATUSES = (
    "draft",
    "ready-to-send",
    "sent",
    "partially-approved",
    "approved",
    "generated",
    "submitted",
    "archived",
    "cancelled",
)

AUTHOR_APPROVAL_STATUSES = (
    "pending",
    "sent",
    "approved",
    "declined",
    "needs-follow-up",
)

WORKFLOW_TYPES = ("authorship-change", "copublication")

VALID_REQUEST_TRANSITIONS = {
    "draft": {"ready-to-send", "cancelled"},
    "ready-to-send": {"sent", "cancelled"},
    "sent": {"partially-approved", "approved", "cancelled"},
    "partially-approved": {"approved", "cancelled"},
    "approved": {"generated"},
    "generated": {"submitted"},
    "submitted": {"archived"},
    "archived": set(),
    "cancelled": set(),
}


@dataclass(frozen=True)
class TableSpec:
    name: str
    columns: tuple[str, ...]


TABLES = {
    "requests": TableSpec(
        "requests",
        (
            "request_id",
            "workflow_type",
            "review_title",
            "review_identifier",
            "contact_author_name",
            "created_date",
            "due_date",
            "current_status",
            "completion_date",
            "dashboard_export_status",
        ),
    ),
    "authors": TableSpec(
        "authors",
        (
            "author_approval_id",
            "request_id",
            "author_name",
            "author_role",
            "display_order",
            "approval_status",
            "date_sent",
            "date_approved",
            "last_reminder_sent",
            "reminder_due",
        ),
    ),
    "approval_events": TableSpec(
        "approval_events",
        (
            "event_id",
            "request_id",
            "author_approval_id",
            "event_type",
            "event_timestamp",
            "actor_role",
            "approval_method",
            "comments",
        ),
    ),
    "reminder_events": TableSpec(
        "reminder_events",
        (
            "reminder_id",
            "request_id",
            "author_approval_id",
            "reminder_type",
            "sent_at",
            "sent_by",
            "reminder_number",
            "delivery_status",
            "next_reminder_due",
        ),
    ),
    "generated_documents": TableSpec(
        "generated_documents",
        (
            "document_id",
            "request_id",
            "workflow_type",
            "template_version",
            "generated_at",
            "generated_by",
            "document_status",
        ),
    ),
    "dashboard_exports": TableSpec(
        "dashboard_exports",
        (
            "request_id",
            "workflow_type",
            "review_title",
            "review_identifier",
            "total_authors",
            "approved_authors",
            "outstanding_authors",
            "current_status",
            "last_reminder_sent",
            "reminder_due",
            "waiting_on",
            "last_exported_at",
        ),
    ),
    "project_status": TableSpec(
        "project_status",
        (
            "review_identifier",
            "review_title",
            "project_phase",
            "priority",
            "owner_role",
            "status_as_of",
            "next_milestone_due",
        ),
    ),
}


# CSV cells are text; these columns may be blank. Everything else is required.
OPTIONAL_COLUMNS = {
    "requests": {"completion_date"},
    "authors": {"date_sent", "date_approved", "last_reminder_sent", "reminder_due"},
    "approval_events": {"author_approval_id", "approval_method", "comments"},
    "reminder_events": {"next_reminder_due"},
    "generated_documents": set(),
    "dashboard_exports": {"last_reminder_sent", "reminder_due", "waiting_on"},
    "project_status": set(),
}
DATE_COLUMNS = {
    "requests": {"created_date", "due_date", "completion_date"},
    "authors": {"date_sent", "date_approved", "last_reminder_sent", "reminder_due"},
    "approval_events": {"event_timestamp"},
    "reminder_events": {"sent_at", "next_reminder_due"},
    "generated_documents": {"generated_at"},
    "dashboard_exports": {"last_reminder_sent", "reminder_due", "last_exported_at"},
    "project_status": {"status_as_of", "next_milestone_due"},
}
INTEGER_COLUMNS = {
    "authors": {"display_order"},
    "reminder_events": {"reminder_number"},
    "dashboard_exports": {"total_authors", "approved_authors", "outstanding_authors"},
}
