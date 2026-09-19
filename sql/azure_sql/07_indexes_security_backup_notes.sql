CREATE NONCLUSTERED INDEX ix_request_status_due
ON core.request (current_status, due_date)
INCLUDE (workflow_type_code, review_identifier, review_title);
GO

CREATE NONCLUSTERED INDEX ix_author_request_status
ON core.author_approval (request_id, approval_status)
INCLUDE (date_sent, date_approved, reminder_due);
GO

CREATE NONCLUSTERED INDEX ix_approval_event_request_time
ON core.approval_event (request_id, event_timestamp)
INCLUDE (event_type, actor_role, author_approval_id);
GO

CREATE NONCLUSTERED INDEX ix_fact_lifecycle_status_due
ON mart.fact_request_lifecycle (current_status_key, due_date_key)
INCLUDE (workflow_type_key, total_authors, approved_authors, outstanding_authors);
GO

CREATE ROLE research_ops_reader;
CREATE ROLE research_ops_loader;
GO

GRANT SELECT ON SCHEMA::rpt TO research_ops_reader;
GRANT SELECT ON SCHEMA::mart TO research_ops_reader;
GRANT SELECT, INSERT, UPDATE, DELETE ON SCHEMA::stg TO research_ops_loader;
GRANT SELECT, INSERT, UPDATE ON SCHEMA::core TO research_ops_loader;
GRANT SELECT, INSERT, UPDATE ON SCHEMA::mart TO research_ops_loader;
GO

/*
Illustrative operational notes; no Azure deployment or cost/restore validation:

1. Verify service-specific cost controls before any authorized deployment.
2. Use only generated fixtures in any portfolio database.
3. Use Azure portal metrics for vCore consumption and storage use.
4. Export a bacpac or use point-in-time restore for recovery demonstrations.
5. Store SQL credentials outside git, preferably in GitHub Actions secrets.
6. Do not grant direct access to staging schemas for reporting users.
*/

