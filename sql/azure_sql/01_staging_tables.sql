CREATE TABLE stg.requests (
    request_id              varchar(20)     NOT NULL,
    workflow_type           varchar(40)     NOT NULL,
    review_title            nvarchar(300)   NOT NULL,
    review_identifier       varchar(30)     NOT NULL,
    contact_author_name     nvarchar(200)   NOT NULL,
    created_date            date            NOT NULL,
    due_date                date            NOT NULL,
    current_status          varchar(40)     NOT NULL,
    completion_date         date            NULL,
    dashboard_export_status varchar(40)     NOT NULL,
    CONSTRAINT pk_stg_requests PRIMARY KEY CLUSTERED (request_id)
);
GO

CREATE TABLE stg.authors (
    author_approval_id varchar(30)   NOT NULL,
    request_id         varchar(20)   NOT NULL,
    author_name        nvarchar(200) NOT NULL,
    author_role        varchar(40)   NOT NULL,
    display_order      int           NOT NULL,
    approval_status    varchar(40)   NOT NULL,
    date_sent          date          NULL,
    date_approved      date          NULL,
    last_reminder_sent date          NULL,
    reminder_due       date          NULL,
    CONSTRAINT pk_stg_authors PRIMARY KEY CLUSTERED (author_approval_id)
);
GO

CREATE TABLE stg.approval_events (
    event_id           varchar(40)    NOT NULL,
    request_id         varchar(20)    NOT NULL,
    author_approval_id varchar(30)    NULL,
    event_type         varchar(60)    NOT NULL,
    event_timestamp    datetime2(0)   NOT NULL,
    actor_role         varchar(60)    NOT NULL,
    approval_method    varchar(60)    NULL,
    comments           nvarchar(1000) NULL,
    CONSTRAINT pk_stg_approval_events PRIMARY KEY CLUSTERED (event_id)
);
GO

CREATE TABLE stg.reminder_events (
    reminder_id        varchar(40)  NOT NULL,
    request_id         varchar(20)  NOT NULL,
    author_approval_id varchar(30)  NOT NULL,
    reminder_type      varchar(40)  NOT NULL,
    sent_at            date         NULL,
    sent_by            varchar(100) NOT NULL,
    reminder_number    int          NOT NULL,
    delivery_status    varchar(40)  NOT NULL,
    next_reminder_due  date         NULL,
    CONSTRAINT pk_stg_reminder_events PRIMARY KEY CLUSTERED (reminder_id)
);
GO

CREATE TABLE stg.generated_documents (
    document_id      varchar(30)  NOT NULL,
    request_id       varchar(20)  NOT NULL,
    workflow_type    varchar(40)  NOT NULL,
    template_version varchar(30)  NOT NULL,
    generated_at     datetime2(0) NOT NULL,
    generated_by     varchar(100) NOT NULL,
    document_status  varchar(40)  NOT NULL,
    CONSTRAINT pk_stg_generated_documents PRIMARY KEY CLUSTERED (document_id)
);
GO

CREATE TABLE stg.dashboard_exports (
    request_id          varchar(20)   NOT NULL,
    workflow_type       varchar(40)   NOT NULL,
    review_title        nvarchar(300) NOT NULL,
    review_identifier   varchar(30)   NOT NULL,
    total_authors       int           NOT NULL,
    approved_authors    int           NOT NULL,
    outstanding_authors int           NOT NULL,
    current_status      varchar(40)   NOT NULL,
    last_reminder_sent  date          NULL,
    reminder_due        date          NULL,
    waiting_on          varchar(100)  NULL,
    last_exported_at    datetime2(0)  NOT NULL,
    CONSTRAINT pk_stg_dashboard_exports PRIMARY KEY CLUSTERED (request_id)
);
GO

CREATE TABLE stg.project_status (
    review_identifier  varchar(30)   NOT NULL,
    review_title       nvarchar(300) NOT NULL,
    project_phase      varchar(60)   NOT NULL,
    priority           varchar(20)   NOT NULL,
    owner_role         varchar(60)   NOT NULL,
    status_as_of       date          NOT NULL,
    next_milestone_due date          NOT NULL,
    CONSTRAINT pk_stg_project_status PRIMARY KEY CLUSTERED (review_identifier)
);
GO

