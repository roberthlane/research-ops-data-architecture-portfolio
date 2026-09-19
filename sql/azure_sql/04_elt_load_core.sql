SET XACT_ABORT ON;
GO

BEGIN TRANSACTION;

MERGE core.workflow_type AS target
USING (
    SELECT 'authorship-change', 'Authorship change'
    UNION ALL SELECT 'copublication', 'Co-publication'
) AS source(workflow_type_code, workflow_label)
ON target.workflow_type_code = source.workflow_type_code
WHEN MATCHED THEN
    UPDATE SET workflow_label = source.workflow_label, is_active = 1
WHEN NOT MATCHED THEN
    INSERT (workflow_type_code, workflow_label) VALUES (source.workflow_type_code, source.workflow_label);

MERGE core.request_status AS target
USING (
    SELECT 'draft', 'Draft', 0
    UNION ALL SELECT 'ready-to-send', 'Ready to send', 0
    UNION ALL SELECT 'sent', 'Sent', 0
    UNION ALL SELECT 'partially-approved', 'Partially approved', 0
    UNION ALL SELECT 'approved', 'Approved', 0
    UNION ALL SELECT 'generated', 'Generated', 0
    UNION ALL SELECT 'submitted', 'Submitted', 1
    UNION ALL SELECT 'archived', 'Archived', 1
    UNION ALL SELECT 'cancelled', 'Cancelled', 1
) AS source(status_code, status_label, terminal_flag)
ON target.status_code = source.status_code
WHEN MATCHED THEN
    UPDATE SET status_label = source.status_label, terminal_flag = source.terminal_flag
WHEN NOT MATCHED THEN
    INSERT (status_code, status_label, terminal_flag)
    VALUES (source.status_code, source.status_label, source.terminal_flag);

MERGE core.request AS target
USING stg.requests AS source
ON target.request_id = source.request_id
WHEN MATCHED THEN
    UPDATE SET
        workflow_type_code = source.workflow_type,
        review_title = source.review_title,
        review_identifier = source.review_identifier,
        contact_author_name = source.contact_author_name,
        created_date = source.created_date,
        due_date = source.due_date,
        current_status = source.current_status,
        completion_date = source.completion_date,
        dashboard_export_status = source.dashboard_export_status,
        updated_at = sysdatetime()
WHEN NOT MATCHED THEN
    INSERT (
        request_id,
        workflow_type_code,
        review_title,
        review_identifier,
        contact_author_name,
        created_date,
        due_date,
        current_status,
        completion_date,
        dashboard_export_status
    )
    VALUES (
        source.request_id,
        source.workflow_type,
        source.review_title,
        source.review_identifier,
        source.contact_author_name,
        source.created_date,
        source.due_date,
        source.current_status,
        source.completion_date,
        source.dashboard_export_status
    );

MERGE core.author_approval AS target
USING stg.authors AS source
ON target.author_approval_id = source.author_approval_id
WHEN MATCHED THEN
    UPDATE SET
        request_id = source.request_id,
        author_name = source.author_name,
        author_role = source.author_role,
        display_order = source.display_order,
        approval_status = source.approval_status,
        date_sent = source.date_sent,
        date_approved = source.date_approved,
        last_reminder_sent = source.last_reminder_sent,
        reminder_due = source.reminder_due,
        updated_at = sysdatetime()
WHEN NOT MATCHED THEN
    INSERT (
        author_approval_id,
        request_id,
        author_name,
        author_role,
        display_order,
        approval_status,
        date_sent,
        date_approved,
        last_reminder_sent,
        reminder_due
    )
    VALUES (
        source.author_approval_id,
        source.request_id,
        source.author_name,
        source.author_role,
        source.display_order,
        source.approval_status,
        source.date_sent,
        source.date_approved,
        source.last_reminder_sent,
        source.reminder_due
    );

INSERT INTO core.approval_event (
    event_id,
    request_id,
    author_approval_id,
    event_type,
    event_timestamp,
    actor_role,
    approval_method,
    comments
)
SELECT
    event_id,
    request_id,
    author_approval_id,
    event_type,
    event_timestamp,
    actor_role,
    approval_method,
    comments
FROM stg.approval_events AS source
WHERE NOT EXISTS (
    SELECT 1 FROM core.approval_event AS target WHERE target.event_id = source.event_id
);

INSERT INTO core.reminder_event (
    reminder_id,
    request_id,
    author_approval_id,
    reminder_type,
    sent_at,
    sent_by,
    reminder_number,
    delivery_status,
    next_reminder_due
)
SELECT
    reminder_id,
    request_id,
    author_approval_id,
    reminder_type,
    sent_at,
    sent_by,
    reminder_number,
    delivery_status,
    next_reminder_due
FROM stg.reminder_events AS source
WHERE NOT EXISTS (
    SELECT 1 FROM core.reminder_event AS target WHERE target.reminder_id = source.reminder_id
);

INSERT INTO core.generated_document (
    document_id,
    request_id,
    workflow_type,
    template_version,
    generated_at,
    generated_by,
    document_status
)
SELECT
    document_id,
    request_id,
    workflow_type,
    template_version,
    generated_at,
    generated_by,
    document_status
FROM stg.generated_documents AS source
WHERE NOT EXISTS (
    SELECT 1 FROM core.generated_document AS target WHERE target.document_id = source.document_id
);

COMMIT TRANSACTION;
GO

