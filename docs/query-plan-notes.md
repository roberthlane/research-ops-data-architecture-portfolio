# Query and index notes

The open-queue view uses the shared status lookup's terminal flag and computes
days-until-due at query time. Indexes on request status/deadline and lifecycle
status/deadline support that access pattern; actual engine plans determine whether
those indexes help at a given scale.

The stale-export procedure compares `last_exported_at` directly with a cutoff at
UTC midnight minus the allowed calendar-day age. Exactly two days old passes a
2-day threshold; one second earlier fails. The timestamp index is available for
range access, without wrapping the indexed column in DATEDIFF in the predicate.

`vw_reminder_approval_status` counts reminders and currently approved linked authors.
It does not claim that reminders caused approval or that approvals occurred afterward.
Cycle-time reporting aggregates completed lifecycle facts by workflow.

No query-speed improvement is claimed without measured engine execution plans.
