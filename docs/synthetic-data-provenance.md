# Synthetic-data provenance

`synthetic.py` generates every committed CSV from local constants and arithmetic.
It reads no source dataset, document, API, or operational system. `SYN-REVIEW-NNNN`,
`Synthetic review topic NN`, and `Demo Author NN` are invented placeholders.
Document rows contain metadata only; no messages or documents are sent/generated.

A fixed reference date in `models.REFERENCE_DATE` makes the fixtures reproducible.
Request lifecycle events, author send/approval dates, contact identity, completion
and document dates use one timeline. Pending/cancelled requests have no invented
send events; sent requests have zero approvals; partially approved requests have
some; completed requests have all authors approved. Cancelled states do not imply
active follow-up, even though unapproved authors remain in the counts.

The demo compares every committed CSV with fresh generation and compares two runs
byte for byte using explicit checks that remain active under Python optimization.
Freshness is measured against the reference date, not the day a reviewer runs it.
The MIT licence covers these generated fixtures with the project.
