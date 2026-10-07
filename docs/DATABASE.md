# Doka Database

## Current authority
Personal Local uses local application state where configured. Personal Cloud uses Supabase Postgres as the current metadata/authz data boundary.

## Security model
Backend/Worker owns database access. Browser code must never receive service-role credentials. RLS is defense-in-depth and does not replace API authorization. Owner checks must be performed from the authenticated identity.

## Migrations
Schema changes use the repository's migration system. Prefer forward corrective migrations over destructive downgrade. Repository head and live production head are separate facts.

Repository head: `20261007120000_doka_trigger_function_least_privilege`.
Prior audited live head: `20261005113241_doka_audit_export_backup_actions`.

## Cloud controls
Doka document/version tables use owner-scoped RLS. Version pointer functions require authenticated owner validation. Bulk mutations are atomic and owner-scoped.

## D1/Turso material
D1/Turso migration material is future/deferred architecture, not current production database authority. Do not dual-write or switch the active Worker without staging, isolation, rollback and remote integration evidence.
