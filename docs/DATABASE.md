# Doka Database

> **Live migration and RPC reconciliation — 2026-10-17**
>
> - Production project `jkobgssaqifzrqfirdfu` remains ACTIVE_HEALTHY. Its latest listed migration is `20261009083942_doka_trigger_function_least_privilege`; it does **not** include `20261017100000_doka_rpc_security_hardening.sql`.
> - Staging project `gzxybtqquzycogaowdbj` remains ACTIVE_HEALTHY and has migrations `20261016094050_staging_doka_core_schema_rls_storage` and `20261017081123_doka_rpc_security_hardening`. The hardened migration is staging-only.
> - Staging SQL checks verified fixed search paths and explicit `auth.uid()` ownership checks for four sensitive RPCs; unauthenticated negative tests and transaction-scoped lifecycle/version/restore/bulk-trash/cross-user tests passed with fixtures rolled back. This is not a substitute for authenticated HTTP User A/B acceptance.
> - The staging Security Advisor reports a generic warning for the four SECURITY DEFINER RPCs callable by authenticated users. Review this finding against fixed search paths, owner checks, restricted EXECUTE grants and live A/B evidence before considering any production rollout.
> - Production Security Advisor reports leaked-password protection disabled; the current Supabase plan does not expose the HaveIBeenPwned-based control. Do not describe this warning as fixed.
>
> ---

> **Owner:** How is Doka's database, migration, ownership and RLS boundary maintained?
> **Update when:** Schema, migration heads, RLS, RPC/function privileges, ownership checks or database providers change.
> **Last Updated:** 2026-10-08
> **Do NOT put here:** Release-gate status, deployment credentials, or provider-specific recovery runbooks.

## Current authority
Personal Local uses local application state where configured. Personal Cloud uses Supabase Postgres as the current metadata/authz data boundary.

## Live verification — 2026-10-08
- Supabase project: Enterprise AI DMS
- Project ref: jkobgssaqifzrqfirdfu
- Status: ACTIVE_HEALTHY
- PostgreSQL: 17.6.1
- Latest live migration: 20261005113241_doka_audit_export_backup_actions

## Security model
Backend/Worker owns database access. Browser code must never receive service-role credentials. RLS is defense-in-depth and does not replace API authorization. Owner checks must be performed from the authenticated identity.

## Migrations
Schema changes use the repository's migration system. Prefer forward corrective migrations over destructive downgrade. Repository head and live production head are separate facts.

Repository head: 20261007120000_doka_trigger_function_least_privilege.
Last audited live head: 20261005113241_doka_audit_export_backup_actions.

These are NOT the same state. The live head must be freshly verified before release.

## Cloud controls
Doka document/version tables use owner-scoped RLS. Version pointer functions require authenticated owner validation. Bulk mutations are atomic and owner-scoped.

Live database health and migration state do not close Gate 10. Two real authenticated users must still demonstrate cross-user API/RLS/Storage denial and owner-scoped access.

## Deferred database material
D1/Turso migration material is future/deferred architecture, not current production database authority. Do not dual-write or switch the active Worker without staging, isolation, rollback and remote integration evidence.
