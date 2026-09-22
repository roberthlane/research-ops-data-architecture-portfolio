# ADR: Declare grain and version policy

## Context

Workflow history and current reporting answer different questions.

## Decision

Use one lifecycle fact per request with core-derived counts; model author versions as daily snapshots with same-day coalescing. Declare only the implemented fact and its dimensions.

## Consequences

Core events preserve finer-grained changes, and core reminders retain operational records.
Dashboard exports stay in staging for reconciliation. Backdated history repair and
additional analytical grains remain outside this implementation.
