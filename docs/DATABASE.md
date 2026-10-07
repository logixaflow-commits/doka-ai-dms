# Doka Database

> **Owner:** How is Doka's database, migration, ownership and RLS boundary maintained?
> **Update when:** Schema, migration heads, RLS, RPC/function privileges, ownership checks or database providers change.
> **Last Updated:** 2026-10-08
> **Do NOT put here:** Release-gate status, deployment credentials, or provider-specific recovery runbooks.

## Current authority
Personal Local uses local application state where configured. Personal Cloud uses Supabase Postgres as the current metadata/authz data boundary.

## Security model
Backend/Worker owns database access. Browser code must never receive service-role credentials. RLS is defense-in-depth and does not replace API authorization. Owner checks must be performed from the authenticated identity.

## Migrations
Schema changes use the repository's migration system. Prefer forward corrective migrations over destructive downgrade. Repository head and live production head are separate facts.

Repository head: `20261007120000_doka_trigger_function_least_privilege`.
Last audited live head: `20261005113241_doka_audit_export_backup_actions`.

These are NOT the same state. The live head must be freshly verified before release claims.

## Cloud controls
Doka document/version tables use owner-scoped RLS. Version pointer functions require authenticated owner validation. Bulk mutations are atomic and owner-scoped.

## Deferred database material
D1/Turso migration material is future/deferred architecture, not current production database authority. Do not dual-write or switch the active Worker without staging, isolation, rollback and remote integration evidence.
