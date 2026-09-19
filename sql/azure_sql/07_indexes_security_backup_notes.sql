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

-- Reporting procedures may read underlying tables through same-owner ownership
-- chains. Reader users receive no direct core/staging SELECT permission.
GRANT EXECUTE ON OBJECT::rpt.usp_request_lifecycle_summary TO research_ops_reader;
GRANT EXECUTE ON OBJECT::rpt.usp_stale_dashboard_exports TO research_ops_reader;
GO

CREATE NONCLUSTERED INDEX ix_dashboard_export_time
ON stg.dashboard_exports(last_exported_at);
GO
