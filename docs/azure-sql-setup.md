# SQL Server integration test

On an amd64 Linux Docker engine, from the repository root:

```bash
PYTHONPATH=src python3 scripts/test_sql_server.py --accept-eula
```

The explicit flag accepts Microsoft's SQL Server container EULA for a disposable
Developer edition test. The script uses an official image pinned by digest, creates
a random container and password, exposes no host ports, mounts no volumes, and removes
only its own container when finished. It does not connect to an existing database.

The test validates synthetic CSVs, imports them into typed staging, executes all
schema/load/reporting/permission scripts, and checks:

- Initial and unchanged repeated core/mart loads.
- Later-day author history with unchanged source send date, same-day coalescing,
  rejection of backdated loads, and preservation after failure.
- Lifecycle fact counts after dashboard staging is cleared.
- Reader access to views/procedures and denial of direct staging/core table access.
- Freshness at the exact two-calendar-day boundary.

CI contains a dedicated engine job. The revised job has not yet executed at this
revision; local validation currently covers SQLite, unit tests, formatting, typing,
and package build. First-run DDL creates an empty schema; it is not a migration tool.
