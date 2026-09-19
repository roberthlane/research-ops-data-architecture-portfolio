# ADR: Separate local and engine validation

## Context

Reviewers may not have SQL Server or a supported container host.

## Decision

Keep a dependency-free SQLite demonstration and a separate disposable SQL Server integration job.

## Consequences

SQLite tests do not establish T-SQL behavior; the engine job must provide its own passing evidence.
