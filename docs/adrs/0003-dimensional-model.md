# ADR: Declare grain and version policy

## Context

Workflow history and current reporting answer different questions.

## Decision

Use one lifecycle fact per request with core-derived counts; model author versions as daily snapshots with same-day coalescing.

## Consequences

Events preserve finer-grained changes. Backdated history repair and additional fact loaders remain outside this implementation.
