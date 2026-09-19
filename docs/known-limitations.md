# Scope and remaining work

- This is a tiny synthetic workflow sample, not a production service or scale benchmark.
- SQLite uses fresh in-memory rebuilds; it does not implement persistence, incremental
  updates, concurrent ingestion, source deletion, or author-version updates.
- SQL Server uses daily SCD snapshots. Multiple changes on a day coalesce, so intraday
  audit history belongs in events rather than author versions. Backdated loads are rejected;
  late-arriving history repair is not implemented.
- Event/reminder/dashboard-snapshot fact tables are design declarations without loaders.
  Project context is staged without downstream transformation.
- Input checks cover the documented contract, not every possible business rule. A report
  cannot be written if the report destination itself is inaccessible. Dates are ISO and
  timezone-naive in the synthetic CSVs; no cross-timezone ingestion is modeled.
- T-SQL first-run schema scripts are not migrations. Core upserts do not propagate source
  deletions; event IDs are append-only. The calendar uses English month/weekday labels.
- Engine validation covers SQL Server 2022 Developer on amd64 Linux using the synthetic
  fixtures. Azure SQL deployment, other engine versions, and scale are not tested.
