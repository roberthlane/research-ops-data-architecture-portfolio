# Case study: approval workflow reporting

A hypothetical research team wants to know which requests await authors, how long
completed workflows take, and whether dashboard extracts agree with source records.
The project turns that problem into explicit grains, keys, lifecycle rules, and
reproducible failure cases using entirely invented inputs.

## Decisions

Raw staging preserves invalid inputs long enough to explain why they fail. Constrained
core tables protect relational entities. A one-row-per-request lifecycle fact derives
counts from core authors, while dashboard exports provide an independent reconciliation
surface. The CLI writes failure reports before stopping; tests exercise actual input files.

SQLite makes the example easy to run without infrastructure. T-SQL expresses a larger
schema and daily versioning policy; a separate engine test checks behavior that SQLite
cannot establish. Same-day author updates coalesce into one daily snapshot, avoiding
ambiguous overlapping intervals while event rows remain the place for detailed history.

## Walkthrough

1. Run the demo and trace one request from CSV through core into its lifecycle fact.
2. Change a contact name, count, status, or timestamp in a scratch CSV and run the CLI
   with `--skip-generate`; inspect the failure report and exit status.
3. Explain why counts come from core rather than dashboard staging, and why the fact
   reconciliation compares values as well as row counts.
4. Review the SCD load-day policy and the engine tests for unchanged, later-day,
   same-day, and backdated loads.
5. Discuss one next requirement: persistent/incremental loading, late-arriving history,
   source deletions, or measured scale. Each changes the current design contract.

The evidence establishes software behavior on generated fixtures. It makes no claim
of organizational adoption or operational savings.
