CREATE TABLE core.workflow_type (
    workflow_type_code varchar(40)  NOT NULL,
    workflow_label     varchar(100) NOT NULL,
    is_active          bit          NOT NULL CONSTRAINT df_workflow_type_active DEFAULT (1),
    CONSTRAINT pk_workflow_type PRIMARY KEY CLUSTERED (workflow_type_code)
);
GO

CREATE TABLE core.request_status (
    status_code varchar(40)  NOT NULL,
    status_label varchar(100) NOT NULL,
    terminal_flag bit NOT NULL,
    CONSTRAINT pk_request_status PRIMARY KEY CLUSTERED (status_code)
);
GO

CREATE TABLE core.request (
    request_id              varchar(20)    NOT NULL,
    workflow_type_code      varchar(40)    NOT NULL,
    review_title            nvarchar(300)  NOT NULL,
    review_identifier       varchar(30)    NOT NULL,
    contact_author_name     nvarchar(200)  NOT NULL,
    created_date            date           NOT NULL,
    due_date                date           NOT NULL,
    current_status          varchar(40)    NOT NULL,
    completion_date         date           NULL,
    dashboard_export_status varchar(40)    NOT NULL,
    inserted_at             datetime2(0)   NOT NULL CONSTRAINT df_request_inserted_at DEFAULT (sysdatetime()),
    updated_at              datetime2(0)   NOT NULL CONSTRAINT df_request_updated_at DEFAULT (sysdatetime()),
    CONSTRAINT pk_request PRIMARY KEY CLUSTERED (request_id),
    CONSTRAINT uq_request_review_identifier UNIQUE (review_identifier),
    CONSTRAINT fk_request_workflow_type FOREIGN KEY (workflow_type_code) REFERENCES core.workflow_type(workflow_type_code),
    CONSTRAINT fk_request_status FOREIGN KEY (current_status) REFERENCES core.request_status(status_code),
    CONSTRAINT ck_request_dates CHECK (due_date >= created_date),
    CONSTRAINT ck_request_completion CHECK (
        completion_date IS NULL OR completion_date >= created_date
    )
);
GO

CREATE TABLE core.author_approval (
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
    inserted_at        datetime2(0)  NOT NULL CONSTRAINT df_author_approval_inserted_at DEFAULT (sysdatetime()),
    updated_at         datetime2(0)  NOT NULL CONSTRAINT df_author_approval_updated_at DEFAULT (sysdatetime()),
    CONSTRAINT pk_author_approval PRIMARY KEY CLUSTERED (author_approval_id),
    CONSTRAINT fk_author_approval_request FOREIGN KEY (request_id) REFERENCES core.request(request_id),
    CONSTRAINT ck_author_status CHECK (approval_status IN ('pending','sent','approved','declined','needs-follow-up')),
    CONSTRAINT ck_author_display_order CHECK (display_order > 0),
    CONSTRAINT ck_author_approval_dates CHECK (
        date_approved IS NULL OR date_sent IS NULL OR date_approved >= date_sent
    )
);
GO

CREATE TABLE core.approval_event (
    event_id           varchar(40)    NOT NULL,
    request_id         varchar(20)    NOT NULL,
    author_approval_id varchar(30)    NULL,
    event_type         varchar(60)    NOT NULL,
    event_timestamp    datetime2(0)   NOT NULL,
    actor_role         varchar(60)    NOT NULL,
    approval_method    varchar(60)    NULL,
    comments           nvarchar(1000) NULL,
    inserted_at        datetime2(0)   NOT NULL CONSTRAINT df_approval_event_inserted_at DEFAULT (sysdatetime()),
    CONSTRAINT pk_approval_event PRIMARY KEY CLUSTERED (event_id),
    CONSTRAINT fk_approval_event_request FOREIGN KEY (request_id) REFERENCES core.request(request_id),
    CONSTRAINT fk_approval_event_author FOREIGN KEY (author_approval_id) REFERENCES core.author_approval(author_approval_id)
);
GO

CREATE TABLE core.reminder_event (
    reminder_id        varchar(40)  NOT NULL,
    request_id         varchar(20)  NOT NULL,
    author_approval_id varchar(30)  NOT NULL,
    reminder_type      varchar(40)  NOT NULL,
    sent_at            date         NULL,
    sent_by            varchar(100) NOT NULL,
    reminder_number    int          NOT NULL,
    delivery_status    varchar(40)  NOT NULL,
    next_reminder_due  date         NULL,
    inserted_at        datetime2(0) NOT NULL CONSTRAINT df_reminder_event_inserted_at DEFAULT (sysdatetime()),
    CONSTRAINT pk_reminder_event PRIMARY KEY CLUSTERED (reminder_id),
    CONSTRAINT fk_reminder_event_request FOREIGN KEY (request_id) REFERENCES core.request(request_id),
    CONSTRAINT fk_reminder_event_author FOREIGN KEY (author_approval_id) REFERENCES core.author_approval(author_approval_id),
    CONSTRAINT ck_reminder_number CHECK (reminder_number > 0)
);
GO

CREATE TABLE core.generated_document (
    document_id      varchar(30)  NOT NULL,
    request_id       varchar(20)  NOT NULL,
    workflow_type    varchar(40)  NOT NULL,
    template_version varchar(30)  NOT NULL,
    generated_at     datetime2(0) NOT NULL,
    generated_by     varchar(100) NOT NULL,
    document_status  varchar(40)  NOT NULL,
    inserted_at      datetime2(0) NOT NULL CONSTRAINT df_generated_document_inserted_at DEFAULT (sysdatetime()),
    CONSTRAINT pk_generated_document PRIMARY KEY CLUSTERED (document_id),
    CONSTRAINT fk_generated_document_request FOREIGN KEY (request_id) REFERENCES core.request(request_id)
);
GO

