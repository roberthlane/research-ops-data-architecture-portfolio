# Operational extension points

The sample runs offline with synthetic inputs. Moving it into an operational system
would require source authorization, persistent ingestion and rejection records,
transactional incremental loading, deletion rules, identity/access tests, monitoring,
and backup/restore verification.

Useful monitoring would include accepted/rejected row counts, failure categories,
load completion, export age, and source-to-fact reconciliation. The current quality
report is a local validation artifact, not a monitoring service.
