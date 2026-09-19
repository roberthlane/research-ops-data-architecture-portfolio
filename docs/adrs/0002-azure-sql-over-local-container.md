# ADR 0002: Keep the local demonstration independent of SQL Server

Status: local SQLite path accepted; SQL Server runtime validation pending.

Use Python's SQLite module for a credential-free demonstration. Maintain T-SQL
files to express an intended SQL Server/Azure SQL architecture without requiring
reviewers to provision a server.

This trades engine parity for easy local reproduction. SQLite executes only a
subset of the larger design; SQL-file presence tests cannot validate SQL Server
syntax or behavior. Future engine validation must follow a separate authorized
plan and record its own evidence.
