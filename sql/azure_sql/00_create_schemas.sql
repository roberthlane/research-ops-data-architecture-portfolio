/*
Research Operations Data Architecture
Azure SQL / SQL Server schema bootstrap.

Run order:
  00_create_schemas.sql
  01_staging_tables.sql
  02_core_tables.sql
  03_mart_tables.sql
  04_elt_load_core.sql
  05_elt_build_mart.sql
  06_views_and_procs.sql
  07_indexes_security_backup_notes.sql
*/

CREATE SCHEMA stg AUTHORIZATION dbo;
GO

CREATE SCHEMA core AUTHORIZATION dbo;
GO

CREATE SCHEMA mart AUTHORIZATION dbo;
GO

CREATE SCHEMA rpt AUTHORIZATION dbo;
GO

