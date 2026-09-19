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

The [validated CI run](https://github.com/roberthlane/research-ops-data-architecture-portfolio/actions/runs/35457514854)
passed these scenarios on SQL Server 2022 Developer, version 16.0.4295.3,
on amd64 Linux. Python 3.11 and 3.14 checks passed in the same run.
This establishes container-engine behavior; Azure SQL deployment is not tested.

Schema creation and mart loading explicitly set the session options required for
[filtered indexes](https://learn.microsoft.com/en-us/sql/t-sql/statements/create-index-transact-sql?view=sql-server-ver16#required-set-options-for-filtered-indexes),
including QUOTED_IDENTIFIER, so they do not depend on client defaults.
First-run DDL creates an empty schema; it is not a migration tool.
