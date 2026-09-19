"""Generate a field-level dictionary from the versioned T-SQL declarations."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MEANINGS = {
    "request_id": "Stable request natural key; one lifecycle fact per request.",
    "workflow_type": "Workflow code: authorship-change or copublication.",
    "workflow_type_code": "Workflow code: authorship-change or copublication.",
    "workflow_label": "Human-readable workflow label.",
    "review_title": "Invented display title; not a publication title.",
    "review_identifier": "Synthetic local review key (SYN-REVIEW-NNNN).",
    "contact_author_name": "Name of the single author row designated contact author.",
    "created_date": "Request creation day, ISO date in CSV.",
    "due_date": "Request deadline, on or after creation.",
    "current_status": "Latest request lifecycle state; must match the last request event.",
    "completion_date": "Date of the latest generated/submitted/archived state, when applicable.",
    "dashboard_export_status": "Source export state for this request.",
    "author_approval_id": "Request-specific author approval natural key; not a global person ID.",
    "author_name": "Invented author display label.",
    "author_role": "contact author or co-author; exactly one contact per request.",
    "display_order": "Positive author ordering position within the request.",
    "approval_status": "pending, sent, approved, declined, or needs-follow-up.",
    "date_sent": "Day approval was requested; blank before sending.",
    "date_approved": "Day the author approved; present iff author state is approved.",
    "last_reminder_sent": "Most recent reminder day, if any.",
    "reminder_due": "Planned next reminder day, if any.",
    "event_id": "Stable lifecycle or author event natural key.",
    "event_type": "Request state for request events; author-sent or author-approved for author events.",
    "event_timestamp": "Event time, timezone-naive ISO timestamp (seconds) in the synthetic fixture.",
    "actor_role": "Role responsible for the synthetic event.",
    "approval_method": "Attestation mechanism for approval events, otherwise blank.",
    "comments": "Generated event annotation; contains no source document text.",
    "reminder_id": "Stable reminder natural key.",
    "reminder_type": "Synthetic reminder category (follow-up).",
    "sent_at": "Reminder send day; no actual message is sent by this project.",
    "sent_by": "Synthetic sending actor label.",
    "reminder_number": "Positive ordinal reminder number.",
    "delivery_status": "Synthetic delivery state.",
    "next_reminder_due": "Planned follow-up day, if any.",
    "document_id": "Stable generated-document metadata key; no document body is stored.",
    "template_version": "Synthetic template version label.",
    "generated_at": "Document generation event date in the fixture; SQL supports a timestamp.",
    "generated_by": "Synthetic generating actor label.",
    "document_status": "Synthetic output state (needs-review or final).",
    "total_authors": "Number of author approval rows for the request, derived from core in the fact.",
    "approved_authors": "Number of author rows currently approved.",
    "outstanding_authors": "Total minus approved; cancellations remain separate terminal states.",
    "waiting_on": "Summary actor group awaiting action; blank for finished/cancelled requests.",
    "last_exported_at": "Export timestamp used for calendar-day freshness checks.",
    "project_phase": "Synthetic project phase; context-only staging input.",
    "priority": "Synthetic priority label (normal or high).",
    "owner_role": "Synthetic workflow owner role.",
    "status_as_of": "Reference day of the project-status extract.",
    "next_milestone_due": "Planned project milestone day.",
    "is_active": "Whether the workflow code is active.",
    "status_code": "Controlled request lifecycle code.",
    "status_label": "Human-readable request status label.",
    "terminal_flag": "Whether a request status closes the open reporting queue.",
    "inserted_at": "SQL Server ingestion timestamp, default server time.",
    "updated_at": "SQL Server last entity upsert timestamp.",
    "calendar_date": "Calendar day represented by a date-dimension row.",
    "calendar_year": "Four-digit calendar year.",
    "calendar_quarter": "Calendar quarter 1 through 4.",
    "calendar_month": "Calendar month 1 through 12.",
    "month_name": "Month label in the SQL Server session language.",
    "day_of_month": "Day of month 1 through 31.",
    "day_of_week_name": "Weekday label in the SQL Server session language.",
    "is_weekend": "Weekend indicator; the SQL script assumes an English session language.",
    "first_request_id": "First request natural key associated with the review dimension.",
    "effective_start_date": "Inclusive load day starting this author version, not source date_sent.",
    "effective_end_date": "Inclusive last day of a closed version; NULL for the current version.",
    "is_current": "1 for the single open author version; same-day changes coalesce.",
    "cycle_time_days": "Calendar days from request creation to completion; NULL if incomplete.",
}


def meaning(column: str) -> str:
    if column in MEANINGS:
        return MEANINGS[column]
    if column.endswith("_key"):
        return "Surrogate/dimension key; see this table's declared key and foreign-key constraints."
    raise ValueError(f"Document the new field: {column}")


def render() -> str:
    lines = [
        "# Data dictionary",
        "",
        "Generated by `python scripts/build_dictionary.py` from SQL DDL.",
        "Types, nullability, and constraints below describe SQL Server. SQLite stages all CSV cells",
        "as nullable TEXT for validation; its implemented core/mart subset is listed in",
        "[architecture](architecture.md). Blank optional CSV cells become SQL NULL.",
        "",
        "The Python field contract also requires unique natural keys, controlled vocabularies,",
        "matching contact authors, consistent lifecycle dates/states, and reconciled exports.",
        "",
    ]
    for path in sorted((ROOT / "sql/azure_sql").glob("0[1-3]_*.sql")):
        for match in re.finditer(r"CREATE TABLE (\w+\.\w+)\s*\((.*?)\n\);", path.read_text(), re.S):
            table, body = match.groups()
            lines += [
                f"## {table}",
                "",
                f"[SQL declaration](../sql/azure_sql/{path.name})",
                "",
                "| Column | SQL type | Nullable | Meaning |",
                "| --- | --- | --- | --- |",
            ]
            for line in body.splitlines():
                col = re.match(
                    r"\s*(\w+)\s+(\w+(?:\([^)]*\))?)\s+(?:IDENTITY\([^)]*\)\s+)?(NOT NULL|NULL)\b",
                    line,
                )
                if col:
                    name, datatype, null = col.groups()
                    lines.append(
                        f"| `{name}` | `{datatype}` | {'Yes' if null == 'NULL' else 'No'} | {meaning(name)} |"
                    )
            constraints = [
                line.strip().rstrip(",") for line in body.splitlines() if "CONSTRAINT " in line
            ]
            lines += ["", "Declared constraints:", "", *[f"- `{c}`" for c in constraints], ""]
    lines += [
        "`mart.dim_author` also has a filtered unique index allowing one current row per author.",
        "Full multiline CHECK expressions are in the linked SQL declarations; these tables list their names.",
        "",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    (ROOT / "docs/data-dictionary.md").write_text(render(), encoding="utf-8")
