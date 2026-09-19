# ADR 0003: Declare reporting grain explicitly

Status: design accepted; partial implementation.

The lifecycle fact uses one row per request. The broader T-SQL design declares
approval-event, reminder, and dashboard-snapshot facts and conformed dimensions.
Only the lifecycle fact is loaded by the supplied T-SQL mart script; SQLite has
an even smaller subset. See [architecture](../architecture.md).

Explicit grain helps expose join/count errors and makes reporting queries easier
to review. Duplicated attributes are intentional in reporting structures. The
author SCD design remains illustrative: it is not evidence of correct historical
versioning, and the documented interval problems require engine-specific work.
