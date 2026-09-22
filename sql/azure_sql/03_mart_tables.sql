-- Filtered indexes require these settings at creation and when indexed rows change.
SET ANSI_NULLS ON;
SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON;
SET ARITHABORT ON;
SET CONCAT_NULL_YIELDS_NULL ON;
SET QUOTED_IDENTIFIER ON;
SET NUMERIC_ROUNDABORT OFF;
GO

CREATE TABLE mart.dim_date (
    date_key         int         NOT NULL,
    calendar_date    date        NOT NULL,
    calendar_year    int         NOT NULL,
    calendar_quarter tinyint     NOT NULL,
    calendar_month   tinyint     NOT NULL,
    month_name       varchar(20) NOT NULL,
    day_of_month     tinyint     NOT NULL,
    day_of_week_name varchar(20) NOT NULL,
    is_weekend       bit         NOT NULL,
    CONSTRAINT pk_dim_date PRIMARY KEY CLUSTERED (date_key),
    CONSTRAINT uq_dim_date_calendar_date UNIQUE (calendar_date)
);
GO

CREATE TABLE mart.dim_workflow_type (
    workflow_type_key int IDENTITY(1,1) NOT NULL,
    workflow_type_code varchar(40) NOT NULL,
    workflow_label varchar(100) NOT NULL,
    CONSTRAINT pk_dim_workflow_type PRIMARY KEY CLUSTERED (workflow_type_key),
    CONSTRAINT uq_dim_workflow_type_code UNIQUE (workflow_type_code)
);
GO

CREATE TABLE mart.dim_status (
    status_key int IDENTITY(1,1) NOT NULL,
    status_code varchar(40) NOT NULL,
    status_label varchar(100) NOT NULL,
    terminal_flag bit NOT NULL,
    CONSTRAINT pk_dim_status PRIMARY KEY CLUSTERED (status_key),
    CONSTRAINT uq_dim_status_code UNIQUE (status_code)
);
GO

CREATE TABLE mart.dim_review (
    review_key int IDENTITY(1,1) NOT NULL,
    review_identifier varchar(30) NOT NULL,
    review_title nvarchar(300) NOT NULL,
    first_request_id varchar(20) NOT NULL,
    CONSTRAINT pk_dim_review PRIMARY KEY CLUSTERED (review_key),
    CONSTRAINT uq_dim_review_identifier UNIQUE (review_identifier)
);
GO

CREATE TABLE mart.dim_author (
    author_key int IDENTITY(1,1) NOT NULL,
    author_approval_id varchar(30) NOT NULL,
    author_name nvarchar(200) NOT NULL,
    author_role varchar(40) NOT NULL,
    approval_status varchar(40) NOT NULL,
    effective_start_date date NOT NULL,
    effective_end_date date NULL,
    is_current bit NOT NULL,
    CONSTRAINT pk_dim_author PRIMARY KEY CLUSTERED (author_key),
    CONSTRAINT uq_dim_author_scd UNIQUE (author_approval_id, effective_start_date),
    CONSTRAINT ck_dim_author_scd_dates CHECK (
        effective_end_date IS NULL OR effective_end_date >= effective_start_date
    )
);
GO

-- At most one open version per author approval.
CREATE UNIQUE INDEX ux_dim_author_current ON mart.dim_author(author_approval_id)
WHERE is_current = 1;
GO

CREATE TABLE mart.fact_request_lifecycle (
    request_id varchar(20) NOT NULL,
    review_key int NOT NULL,
    workflow_type_key int NOT NULL,
    current_status_key int NOT NULL,
    created_date_key int NOT NULL,
    due_date_key int NOT NULL,
    completion_date_key int NULL,
    cycle_time_days int NULL,
    total_authors int NOT NULL,
    approved_authors int NOT NULL,
    outstanding_authors int NOT NULL,
    CONSTRAINT pk_fact_request_lifecycle PRIMARY KEY CLUSTERED (request_id),
    CONSTRAINT fk_fact_lifecycle_review FOREIGN KEY (review_key) REFERENCES mart.dim_review(review_key),
    CONSTRAINT fk_fact_lifecycle_workflow FOREIGN KEY (workflow_type_key) REFERENCES mart.dim_workflow_type(workflow_type_key),
    CONSTRAINT fk_fact_lifecycle_status FOREIGN KEY (current_status_key) REFERENCES mart.dim_status(status_key),
    CONSTRAINT fk_fact_lifecycle_created_date FOREIGN KEY (created_date_key) REFERENCES mart.dim_date(date_key),
    CONSTRAINT fk_fact_lifecycle_due_date FOREIGN KEY (due_date_key) REFERENCES mart.dim_date(date_key),
    CONSTRAINT fk_fact_lifecycle_completion_date FOREIGN KEY (completion_date_key) REFERENCES mart.dim_date(date_key)
);
GO
