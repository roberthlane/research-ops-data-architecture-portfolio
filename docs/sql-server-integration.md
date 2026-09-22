# SQL Server integration test

On an amd64 Linux Docker engine, from the repository root:

```bash
make check-sql PYTHON=python3 SQL_SERVER_ARGS=--accept-eula
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
- Document workflow agreement enforced by the database, including a different valid code.
- Identical calendar keys/labels/weekend flags under French/German and different DATEFIRST settings.

The [baseline validated CI run](https://github.com/roberthlane/research-ops-data-architecture-portfolio/actions/runs/35457514854)
passed the original load/SCD/permission/freshness scenarios on SQL Server 2022 Developer, version 16.0.4295.3,
on amd64 Linux. Python 3.11 and 3.14 checks passed in the same run.
This establishes container-engine behavior; Azure SQL deployment is not tested.
The added workflow-constraint and calendar-language scenarios await their first engine run.
Use the [current workflow](https://github.com/roberthlane/research-ops-data-architecture-portfolio/actions/workflows/ci.yml)
to inspect results for later revisions; a historical passing run does not validate changed SQL.

Schema creation and mart loading explicitly set the session options required for
[filtered indexes](https://learn.microsoft.com/en-us/sql/t-sql/statements/create-index-transact-sql?view=sql-server-ver16#required-set-options-for-filtered-indexes),
including QUOTED_IDENTIFIER, so they do not depend on client defaults.
First-run DDL creates an empty schema; it is not a migration tool.
