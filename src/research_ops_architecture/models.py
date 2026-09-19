from __future__ import annotations

from dataclasses import dataclass


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

