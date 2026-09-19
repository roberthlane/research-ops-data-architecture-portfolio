# Data Dictionary

This lists the larger T-SQL design. For executable SQLite coverage and missing
loaders, see [architecture](architecture.md) and [limitations](known-limitations.md).

## Staging Tables

`stg.requests`: request-level extract from the operational workflow.

Key fields:

- `request_id`: stable request natural key.
- `workflow_type`: controlled workflow value.
- `review_identifier`: explicitly synthetic local key (`SYN-REVIEW-0001`, etc.).
- `current_status`: latest operational status.
- `dashboard_export_status`: export state for downstream monitoring.

`stg.authors`: author approval records.

Key fields:

- `author_approval_id`: stable author approval key.
- `request_id`: parent request key.
- `approval_status`: author-level approval state.
- `date_sent`, `date_approved`: lifecycle dates.

`stg.approval_events`: append-only lifecycle and author approval events.

`stg.reminder_events`: reminder delivery records.

`stg.generated_documents`: generated form/evidence package records.

`stg.dashboard_exports`: synthetic dashboard summary rows; not a privacy guarantee.

`stg.project_status`: synthetic project tracking context.

## Core Tables

`core.request`: normalized request entity.

`core.author_approval`: normalized author approval entity.

`core.approval_event`: append-only event log.

`core.reminder_event`: reminder event log.

`core.generated_document`: generated output metadata.

`core.workflow_type` and `core.request_status`: controlled vocabularies.

## Mart Tables

`mart.dim_date`: conformed calendar dimension.

`mart.dim_review`: one row per review identifier.

`mart.dim_author`: illustrative Type 2 SCD design for author approval status, not runtime-validated.

`mart.dim_workflow_type`: workflow dimension.

`mart.dim_status`: request status dimension.

`mart.fact_approval_event`: one row per lifecycle or approval event.

`mart.fact_request_lifecycle`: one row per request.

`mart.fact_reminder`: one row per reminder.

`mart.fact_dashboard_snapshot`: one row per dashboard export snapshot.

