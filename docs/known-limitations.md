# Known limitations

## Local runtime

- The database is recreated in memory for each run. Insert loaders are not
  incremental, same-connection reruns are not supported, and persistence,
  deletion, concurrent updates, recovery, and scale are untested.
- SQLite implements only the subset listed in [architecture](architecture.md).
  Its status dimension is observed statuses; its author dimension contains only
  initial rows. There is no executable Type 2 history update in SQLite.
- Seven quality checks are selective. They do not validate every vocabulary,
  event-to-current-status agreement, first lifecycle state, chronology, column
  format, or aggregate value. Empty inputs can pass some checks vacuously.
- Duplicate keys and some missing parents fail during loading. Invalid/missing
  timestamps can raise exceptions. The CLI checks after loading/building and
  writes a report only after successful validation; failures need not yield a
  structured FAIL report. Do not call this a production quarantine system.
- Mart/core equality checks only row counts. Lifecycle author counts are copied
  from dashboard summaries. No cross-check against detailed author rows is made.
- Fixed-date freshness and tiny invented records do not measure real operations.

## Unexecuted T-SQL design

- DDL is for first creation, not a migration/rerun tool. No automated CSV loader
  or SQL Server integration test is present. Tests of SQL files check text and
  object presence, not syntax, permissions, execution plans, or runtime behavior.
- Event, reminder, and dashboard-snapshot fact tables are declared but not loaded
  by script 05. Project-status input is staged without a downstream loader.
- Author SCD rows use source `date_sent` as a new version's start while expiring
  a prior version against the current date. Changed rows can overlap historical
  intervals; same-day changes can create invalid intervals. Historical fact
  linkage and late-arriving changes are not implemented or tested.
- The date dimension bounds come from request creation/due dates plus 14 days;
  arbitrary event/completion dates outside the range need handling. SQL uses
  server time while the local quality fixture uses a fixed date.
- The view named `vw_reminder_effectiveness` counts currently approved authors
  linked to reminders. It does not compare approval/reminder timestamps and
  cannot establish approvals after reminders or causal effectiveness.
- Export rows include titles/identifiers and workflow status. In a real system,
  removing emails/tokens alone would not make those records safe to publish.
- Indexes, role grants, cloud cost controls, backups, and restores are proposals.
  None were tested against Azure or SQL Server during release preparation.
