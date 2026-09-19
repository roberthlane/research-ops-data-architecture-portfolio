CREATE OR ALTER VIEW rpt.vw_open_approval_queue AS
SELECT
    r.request_id,
    r.review_identifier,
    r.review_title,
    r.workflow_type_code,
    r.current_status,
    r.due_date,
    f.total_authors,
    f.approved_authors,
    f.outstanding_authors,
    DATEDIFF(day, CONVERT(date, SYSUTCDATETIME()), r.due_date) AS days_until_due
FROM core.request AS r
JOIN mart.fact_request_lifecycle AS f ON f.request_id = r.request_id
JOIN core.request_status AS s ON s.status_code = r.current_status
WHERE s.terminal_flag = 0
  AND f.outstanding_authors > 0;
GO

CREATE OR ALTER VIEW rpt.vw_cycle_time_by_workflow AS
SELECT
    dw.workflow_type_code,
    COUNT(*) AS completed_request_count,
    AVG(CAST(f.cycle_time_days AS decimal(10, 2))) AS avg_cycle_time_days,
    MIN(f.cycle_time_days) AS min_cycle_time_days,
    MAX(f.cycle_time_days) AS max_cycle_time_days
FROM mart.fact_request_lifecycle AS f
JOIN mart.dim_workflow_type AS dw ON dw.workflow_type_key = f.workflow_type_key
WHERE f.cycle_time_days IS NOT NULL
GROUP BY dw.workflow_type_code;
GO

CREATE OR ALTER VIEW rpt.vw_reminder_approval_status AS
SELECT
    r.workflow_type_code,
    COUNT(DISTINCT rem.reminder_id) AS reminders_sent,
    COUNT(DISTINCT CASE WHEN a.approval_status = 'approved' THEN a.author_approval_id END) AS currently_approved_authors
FROM core.reminder_event AS rem
JOIN core.request AS r ON r.request_id = rem.request_id
JOIN core.author_approval AS a ON a.author_approval_id = rem.author_approval_id
GROUP BY r.workflow_type_code;
GO

CREATE OR ALTER PROCEDURE rpt.usp_request_lifecycle_summary
    @workflow_type varchar(40) = NULL
AS
BEGIN
    SET NOCOUNT ON;

    SELECT
        r.workflow_type_code,
        r.current_status,
        COUNT(*) AS request_count,
        SUM(f.total_authors) AS total_authors,
        SUM(f.approved_authors) AS approved_authors,
        SUM(f.outstanding_authors) AS outstanding_authors,
        AVG(CAST(f.cycle_time_days AS decimal(10, 2))) AS avg_cycle_time_days
    FROM core.request AS r
    JOIN mart.fact_request_lifecycle AS f ON f.request_id = r.request_id
    WHERE @workflow_type IS NULL OR r.workflow_type_code = @workflow_type
    GROUP BY r.workflow_type_code, r.current_status
    ORDER BY r.workflow_type_code, r.current_status;
END;
GO

CREATE OR ALTER PROCEDURE rpt.usp_stale_dashboard_exports
    @max_age_days int = 2
AS
BEGIN
    SET NOCOUNT ON;
    IF @max_age_days IS NULL OR @max_age_days < 0 OR @max_age_days > 36500
        THROW 50002, 'max_age_days must be between 0 and 36500.', 1;
    DECLARE @today date = CONVERT(date, SYSUTCDATETIME());

    SELECT
        request_id,
        review_identifier,
        review_title,
        current_status,
        last_exported_at,
        DATEDIFF(day, last_exported_at, @today) AS export_age_days
    FROM stg.dashboard_exports
    WHERE last_exported_at < DATEADD(day, -@max_age_days, CONVERT(datetime2(0), @today))
    ORDER BY export_age_days DESC;
END;
GO
