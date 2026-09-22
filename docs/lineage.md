# Lineage

The generator defines seven CSV extracts. `models.py` defines their exact column
order; malformed headers or row widths produce a failure report. Validation checks
keys, fields, references, vocabularies, request paths, contact identity, approval state, chronology,
export reconciliation, and freshness before core loading.

| Input | Local destination | Reporting use |
| --- | --- | --- |
| requests.csv | stg_requests → core_request | Lifecycle identity, dates, status |
| authors.csv | stg_authors → core_author_approval | Lifecycle counts; initial author dimension |
| approval_events.csv | stg_approval_events → core_approval_event | Lifecycle and author-event validation |
| dashboard_exports.csv | stg_dashboard_exports | Reconciliation/freshness only; not the fact's source |
| reminder_events.csv | stg_reminder_events | Contract validation; T-SQL also loads core reminders |
| generated_documents.csv | stg_generated_documents | Generation chronology; T-SQL also loads core metadata |
| project_status.csv | stg_project_status | Context-only staging; review must belong to this extract |

Post-build reconciliation compares each fact's request key and author counts with
core records. It detects missing/extra facts and wrong counts. SQL reporting computes
relative deadlines at query time and obtains terminal-state meaning from the shared
status lookup. The reminder view reports current approval associations, not an effect
attributed to sending reminders.
