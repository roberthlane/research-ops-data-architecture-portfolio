# Architecture and implementation scope

This personal portfolio project models a hypothetical research approval workflow.
Its only input is generated synthetic CSV data. There is no connection to an
operational system and no automatic publication of records.

| Layer | Executable SQLite subset | T-SQL design |
| --- | --- | --- |
| Staging | All seven CSV tables | All seven staging tables |
| Core | Request, author approval, approval event | Also reminders, document metadata, workflow and status lookup tables |
| Mart | Status dimension, initial author dimension rows, lifecycle fact | Date/review/author/workflow/status dimensions; lifecycle/event/reminder/snapshot facts declared |
| Reporting | Queries in the console demo | Views and stored procedures declared |

SQLite table names use underscores (`core_request`); T-SQL uses schemas
(`core.request`). This is a subset implementation, not an engine-equivalence test.

The lifecycle fact grain is one row per request. Its counts come from the
synthetic dashboard export, not a fresh aggregation of author approvals.
The quality gate compares request and fact row counts, not every metric value.
`stg_project_status` is loaded for context and has no downstream transformation.

A CLI run creates a fresh in-memory database. Repeating the whole CLI rebuild is
reproducible; repeating the insert loaders on the same connection is not an
idempotent update and fails primary-key constraints. The T-SQL upsert design
requires separate runtime, concurrency, transaction, and deletion tests.

The remaining T-SQL facts have DDL but no loaders in script 05. The author
SCD example is illustrative and has effective-date limitations. Read
[known limitations](known-limitations.md) before making warehouse-history claims.
