# Case study: a reproducible workflow data sample

## Problem and approach

A hypothetical research team wants to understand request status, pending approvals,
and workflow duration. This project explores how to separate source-shaped records,
relational entities, and reporting facts without bringing real operational records
into a portfolio repository.

The executable sample generates seven CSVs and loads them into a fresh SQLite
database. It checks specific integrity and lifecycle conditions and builds a
one-row-per-request reporting fact. The companion T-SQL files explore a larger
staging/core/mart/reporting design. They are not a deployed warehouse.

## Decisions a reviewer can inspect

- Fixed-date, invented fixtures make regeneration reviewable in a diff and CI.
- Temporary CSVs and an in-memory database keep the demo free of cloud setup.
- Keys and foreign keys reject some malformed records during loading; additional
  quality checks examine lifecycle transitions, freshness, and fact counts.
- A lifecycle fact makes status summaries simple, but exported counts can disagree
  with source author rows. This sample does not validate all such discrepancies.
- T-SQL and SQLite are maintained separately. That improves local access but creates
  a parity gap; the implementation matrix makes the gap explicit.

## Interview walkthrough

1. Run the tests and `scripts/demo.py`. Explain why the date is fixed and how
   committed fixtures are checked against fresh generation.
2. Trace `SYN-REVIEW-0001` through requests, authors, events, and lifecycle fact.
   Explain the grain and why author-approval IDs are request-specific.
3. Inspect the deliberately stale export and invalid transition in the demo.
   Explain which validator catches each, and which malformed inputs instead
   raise loader exceptions before a quality report can be written.
4. Discuss one limitation: fresh rebuilds are not incremental upserts; the SCD
   example does not establish historical correctness; or equal row counts do not
   prove equal content.
5. Before using first-person employment claims, identify the parts you personally
   designed, reviewed, tested, or changed. Repository presence alone cannot do that.

## Evidence and next validation boundary

The recorded demo and unit tests are local software evidence on tiny synthetic
fixtures. The next engine-specific validation would run the T-SQL in a disposable,
authorized SQL Server environment with explicit data import, rerun tests, and
SCD boundary cases. That work has not been performed. No scale, user adoption,
clinical effectiveness, time saving, or deployment outcome is claimed.
