# SQL Server / Azure SQL validation plan

The T-SQL scripts are unexecuted design artifacts. The supported local demo uses
SQLite and requires no cloud account. This page is a future validation plan, not
a tested deployment runbook or a promise of a free hosted database.

Before an engine trial, review [known limitations](known-limitations.md), choose
an authorized disposable SQL Server-compatible environment, and check its current
terms, version, network access, and cost settings. The `.env.example` file lists
placeholders only; the current Python program does not use those settings.

Suggested trial sequence:

1. On an empty database, inspect and execute scripts 00 through 03 for schemas,
   staging, core, and mart tables.
2. Generate synthetic CSVs locally using the README command. Implement or select
   an importer that maps empty CSV cells to SQL NULL and validates row counts,
   types, and dates. No importer is supplied or verified here.
3. Import all seven CSVs into matching staging tables before running scripts 04
   and 05. Resolve incomplete fact loaders and SCD date behavior as required by
   the intended experiment.
4. Inspect scripts 06 and 07 before creating reporting objects, indexes and roles.
   Test grants with least-privilege identities. These are first-run scripts.
5. Check expected facts, rerun semantics, invalid-input rollback, engine-specific
   errors, date coverage, SCD intervals, and actual query plans. Record the engine
   version and output; SQLite tests do not substitute for this evidence.

Database provisioning, paid usage, credentials, backups, and deployment are
outside this release candidate's validation evidence.
