# Query Plan And Index Notes

These notes document the intended SQL Server tuning exercise. Capture actual
query-plan screenshots after running the scripts in Azure SQL.

## Query 1: Open Approval Queue

Object: `rpt.vw_open_approval_queue`

Expected access pattern:

- filter by nonterminal status;
- filter to requests with outstanding authors;
- order or scan by due date.

Index support:

- `ix_request_status_due` on `core.request`;
- `ix_fact_lifecycle_status_due` on `mart.fact_request_lifecycle`.

## Query 2: Cycle Time By Workflow

Object: `rpt.vw_cycle_time_by_workflow`

Expected access pattern:

- aggregate completed requests by workflow type;
- ignore requests without completion dates.

Index support:

- clustered key on `mart.fact_request_lifecycle(request_id)`;
- dimension keys on workflow and status.

## Query 3: Reminder/approval association (misleading legacy object name)

Object: `rpt.vw_reminder_effectiveness`

The view does not test timestamp order or causal effectiveness. Its
`approvals_after_reminder` alias overstates what the query establishes.

Expected access pattern:

- join reminders to author approvals and requests;
- group by workflow type.

Index support:

- `ix_author_request_status`;
- future improvement: add `ix_reminder_request_author` if the reminder table
  grows.

## Query 4: Request Event Timeline

Expected access pattern:

- retrieve all events for one request ordered by timestamp.

Index support:

- `ix_approval_event_request_time`.

## Query 5: Stale Dashboard Exports

Object: `rpt.usp_stale_dashboard_exports`

Expected access pattern:

- scan dashboard export timestamps and return stale rows.

Future improvement:

- add an index on `stg.dashboard_exports(last_exported_at)` if stale-export
  checks become expensive.

