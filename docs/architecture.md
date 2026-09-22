# Architecture

The sample separates source-shaped records, validated entities, and reporting facts.
CSV headers are exact contracts. Validation groups records by request and author/event
type once, then runs named checks; event ordering is sorted within each request. SQLite staging accepts nullable text so invalid
keys, values, and relationships can be reported together before core insertion.
The CLI persists that report before returning failure. Core keys and foreign keys
provide a second integrity boundary. SQL Server also enforces document/request workflow
agreement with a composite foreign key.

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

The SQL Server mart declares only the implemented lifecycle fact and its dimensions. Approval
events and reminders remain in core; dashboard exports remain in staging for
reconciliation. SQLite does not implement SCD updates. Engine-specific evidence is
recorded separately from local SQLite results.

Quality reports count rule violations within each check, not distinct affected rows.
Contact-author identity and request-state agreement with author approvals have
separate checks, so a failure identifies which rule needs attention.
Each invalid vocabulary cell counts once; each row with a duplicated key is counted.
One row can violate several rules or checks. Details show at most five examples,
while the displayed count includes every violation. Load failures name the table and
a controlled reason, excluding arbitrary filesystem paths and input contents.
