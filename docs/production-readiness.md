# Production-readiness gap

This project is a local synthetic work sample, not a production-ready service.
The checks and CI demonstrate bounded validation; see the explicit
[limitations](known-limitations.md).

A production implementation would need input contracts and rejection handling,
transactional incremental loads, deletion rules, historical-dimension tests,
authentication and least-privilege verification, protected secrets, measured
capacity, monitoring, and tested backup/restore procedures. These controls are
not established by the sample's SQL comments or successful local tests.

CI can test the code, regenerate fixtures, and reject committed-output drift.
Runtime monitoring, if later built, should include per-table row counts, rejected
records, load completion/failure, export age, and reconciliation against source
counts. Synthetic cycle times are not service-level or business-impact evidence.

Real workflow records can remain confidential even after contact details are
removed. Authorize each future source and downstream use separately; do not
replace the fixtures with operational exports in a portfolio repository.
