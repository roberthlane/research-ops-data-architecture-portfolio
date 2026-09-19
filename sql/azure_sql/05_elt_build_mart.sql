-- Required for DML against the filtered current-author index, independent of client defaults.
SET ANSI_NULLS ON;
SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON;
SET ARITHABORT ON;
SET CONCAT_NULL_YIELDS_NULL ON;
SET QUOTED_IDENTIFIER ON;
SET NUMERIC_ROUNDABORT OFF;
SET XACT_ABORT ON;
GO

BEGIN TRANSACTION;

-- Daily Type 2 snapshots. Multiple changes on one load day coalesce into that
-- day's version; a later day expires it and starts a new inclusive interval.
DECLARE @load_date date = COALESCE(
    CONVERT(date, SESSION_CONTEXT(N'load_date')), CONVERT(date, SYSUTCDATETIME())
);
IF EXISTS (SELECT 1 FROM mart.dim_author WHERE is_current = 1 AND effective_start_date > @load_date)
    THROW 50001, 'Backdated dimension loads are not supported.', 1;

;WITH date_bounds AS (
    SELECT MIN(created_date) AS min_date, MAX(due_date) AS max_date FROM core.request
),
date_series AS (
    SELECT min_date AS calendar_date FROM date_bounds
    UNION ALL
    SELECT DATEADD(day, 1, calendar_date)
    FROM date_series
    CROSS JOIN date_bounds
    WHERE calendar_date < DATEADD(day, 14, date_bounds.max_date)
)
INSERT INTO mart.dim_date (
    date_key,
    calendar_date,
    calendar_year,
    calendar_quarter,
    calendar_month,
    month_name,
    day_of_month,
    day_of_week_name,
    is_weekend
)
SELECT
    CONVERT(int, FORMAT(calendar_date, 'yyyyMMdd')),
    calendar_date,
    YEAR(calendar_date),
    DATEPART(quarter, calendar_date),
    MONTH(calendar_date),
    DATENAME(month, calendar_date),
    DAY(calendar_date),
    DATENAME(weekday, calendar_date),
    CASE WHEN DATENAME(weekday, calendar_date) IN ('Saturday', 'Sunday') THEN 1 ELSE 0 END
FROM date_series AS source
WHERE NOT EXISTS (
    SELECT 1 FROM mart.dim_date AS target WHERE target.calendar_date = source.calendar_date
)
OPTION (MAXRECURSION 32767);

MERGE mart.dim_workflow_type AS target
USING core.workflow_type AS source
ON target.workflow_type_code = source.workflow_type_code
WHEN MATCHED THEN UPDATE SET workflow_label = source.workflow_label
WHEN NOT MATCHED THEN
    INSERT (workflow_type_code, workflow_label)
    VALUES (source.workflow_type_code, source.workflow_label);

MERGE mart.dim_status AS target
USING core.request_status AS source
ON target.status_code = source.status_code
WHEN MATCHED THEN UPDATE SET status_label = source.status_label, terminal_flag = source.terminal_flag
WHEN NOT MATCHED THEN
    INSERT (status_code, status_label, terminal_flag)
    VALUES (source.status_code, source.status_label, source.terminal_flag);

MERGE mart.dim_review AS target
USING (
    SELECT review_identifier, MAX(review_title) AS review_title, MIN(request_id) AS first_request_id
    FROM core.request
    GROUP BY review_identifier
) AS source
ON target.review_identifier = source.review_identifier
WHEN MATCHED THEN UPDATE SET review_title = source.review_title
WHEN NOT MATCHED THEN
    INSERT (review_identifier, review_title, first_request_id)
    VALUES (source.review_identifier, source.review_title, source.first_request_id);

-- Coalesce same-day changes without creating zero-length/duplicate intervals.
UPDATE target
SET author_name = source.author_name, author_role = source.author_role,
    approval_status = source.approval_status
FROM mart.dim_author AS target
JOIN core.author_approval AS source ON source.author_approval_id = target.author_approval_id
WHERE target.is_current = 1 AND target.effective_start_date = @load_date;

UPDATE target
SET effective_end_date = DATEADD(day, -1, @load_date), is_current = 0
FROM mart.dim_author AS target
JOIN core.author_approval AS source ON source.author_approval_id = target.author_approval_id
WHERE target.is_current = 1 AND target.effective_start_date < @load_date
  AND (target.author_name <> source.author_name
       OR target.author_role <> source.author_role
       OR target.approval_status <> source.approval_status);

INSERT INTO mart.dim_author (
    author_approval_id, author_name, author_role, approval_status,
    effective_start_date, effective_end_date, is_current
)
SELECT source.author_approval_id, source.author_name, source.author_role,
       source.approval_status, @load_date, NULL, 1
FROM core.author_approval AS source
WHERE NOT EXISTS (
    SELECT 1 FROM mart.dim_author AS target
    WHERE target.author_approval_id = source.author_approval_id AND target.is_current = 1
);

MERGE mart.fact_request_lifecycle AS target
USING (
    SELECT
        r.request_id,
        dr.review_key,
        dw.workflow_type_key,
        ds.status_key AS current_status_key,
        d_created.date_key AS created_date_key,
        d_due.date_key AS due_date_key,
        d_done.date_key AS completion_date_key,
        CASE WHEN r.completion_date IS NULL THEN NULL ELSE DATEDIFF(day, r.created_date, r.completion_date) END AS cycle_time_days,
        ac.total_authors,
        ac.approved_authors,
        ac.outstanding_authors
    FROM core.request AS r
    CROSS APPLY (
        SELECT COUNT(*) AS total_authors,
               COALESCE(SUM(CASE WHEN a.approval_status = 'approved' THEN 1 ELSE 0 END), 0) AS approved_authors,
               COALESCE(SUM(CASE WHEN a.approval_status <> 'approved' THEN 1 ELSE 0 END), 0) AS outstanding_authors
        FROM core.author_approval AS a WHERE a.request_id = r.request_id
    ) AS ac
    JOIN mart.dim_review AS dr ON dr.review_identifier = r.review_identifier
    JOIN mart.dim_workflow_type AS dw ON dw.workflow_type_code = r.workflow_type_code
    JOIN mart.dim_status AS ds ON ds.status_code = r.current_status
    JOIN mart.dim_date AS d_created ON d_created.calendar_date = r.created_date
    JOIN mart.dim_date AS d_due ON d_due.calendar_date = r.due_date
    LEFT JOIN mart.dim_date AS d_done ON d_done.calendar_date = r.completion_date
) AS source
ON target.request_id = source.request_id
WHEN MATCHED THEN UPDATE SET
    review_key = source.review_key,
    workflow_type_key = source.workflow_type_key,
    current_status_key = source.current_status_key,
    created_date_key = source.created_date_key,
    due_date_key = source.due_date_key,
    completion_date_key = source.completion_date_key,
    cycle_time_days = source.cycle_time_days,
    total_authors = source.total_authors,
    approved_authors = source.approved_authors,
    outstanding_authors = source.outstanding_authors
WHEN NOT MATCHED THEN
    INSERT (
        request_id,
        review_key,
        workflow_type_key,
        current_status_key,
        created_date_key,
        due_date_key,
        completion_date_key,
        cycle_time_days,
        total_authors,
        approved_authors,
        outstanding_authors
    )
    VALUES (
        source.request_id,
        source.review_key,
        source.workflow_type_key,
        source.current_status_key,
        source.created_date_key,
        source.due_date_key,
        source.completion_date_key,
        source.cycle_time_days,
        source.total_authors,
        source.approved_authors,
        source.outstanding_authors
    );

COMMIT TRANSACTION;
GO
