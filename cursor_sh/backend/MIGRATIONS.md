# Database Migrations

Production deployments use Alembic instead of application startup `create_all`.
On production startup, the backend now checks both expected tables and
`alembic_version`; a database that was manually created must be stamped before
the service will boot.

## New RDS Database

```bash
cd cursor_sh/backend
alembic upgrade head
```

## Existing Database That Already Matches Current Models

Use this only after verifying table structure and row counts:

```bash
cd cursor_sh/backend
alembic stamp head
```

## Audit Log Database

Production must set `AUDIT_DATABASE_URL` to MySQL/RDS when `LOG_DB_ENABLED=true`.
The audit table is initialized by the backend in the configured audit database;
keep the audit database backed up independently from the main business database.

## Creating Future Revisions

```bash
cd cursor_sh/backend
alembic revision --autogenerate -m "describe_change"
alembic upgrade head
```

Legacy one-off migration scripts are not part of production deployment. Use
Alembic for schema changes, and use a dedicated, tested data migration plan for
SQLite-to-RDS data moves.
