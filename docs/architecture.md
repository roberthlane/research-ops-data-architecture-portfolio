# Architecture

The sample separates source-shaped records, validated entities, and reporting facts.
CSV headers are exact contracts. SQLite staging accepts nullable text so invalid
keys, values, and relationships can be reported together before core insertion.
The CLI persists that report before returning failure. Core keys and foreign keys
provide a second integrity boundary.

| Layer | Executable SQLite | SQL Server scripts |
| --- | --- | --- |
| Staging | Seven permissive text tables | Seven typed tables; integration importer validates CSVs first |
| Core | Request, author approval, approval event | Also reminder, document, workflow, and status tables |
| Mart | Initial author/status dimensions and lifecycle fact | Date/review/workflow/status dimensions, daily author versions, lifecycle fact |
| Reporting | Console summaries | Views and procedures with reader EXECUTE grants |

The lifecycle fact grain is **one row per request**. Author counts come from core
author rows, including zero-author counts via an outer join/aggregate. The workflow
input contract requires one contact author; zero-author input is therefore rejected
before ordinary loading. Dashboard exports are independently reconciled to source
records rather than supplying fact counts.

The CLI creates a new in-memory database each run. This is a deterministic rebuild,
not an incremental SQLite loader. SQL Server uses core upserts and a mart load;
its author SCD uses inclusive daily intervals, one current row per author, same-day
coalescing, and rejection of backdated loads. `SESSION_CONTEXT('load_date')` controls
the test load day; the default is the current UTC day. Source send dates never serve
as version keys.

Three additional T-SQL facts (event, reminder, snapshot) are declared design targets
without loaders. SQLite does not implement SCD updates. Engine-specific evidence
is recorded separately from local SQLite results.
