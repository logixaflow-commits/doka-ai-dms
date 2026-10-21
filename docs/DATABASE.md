# Doka Database

> **Live read-only RPC recheck — 2026-10-21 05:16 UTC**
>
> - Both production (`jkobgssaqifzrqfirdfu`) and staging (`gzxybtqquzycogaowdbj`) have RLS enabled on `doka_documents`, `doka_document_versions`, and `doka_audit_events`.
> - Production's four sensitive RPCs are `SECURITY INVOKER`; EXECUTE is granted to `authenticated` only (not `anon` or `service_role`). Their existing search paths are `public` or `public, pg_temp`. Authenticated users cannot directly update storage-pointer columns, so version replacement/restore runtime acceptance remains unverified and may fail.
> - Staging's four sensitive RPCs are `SECURITY DEFINER`; EXECUTE is available to `authenticated` and `service_role`, not `anon`. Search path is `pg_catalog, public, pg_temp`. Security Advisor reports four authenticated-callable SECURITY DEFINER warnings; owner checks and least-privilege behavior require real staging A/B evidence.
> - Production's migration ledger lists 32 entries, including the RPC hardening apply and compensating rollback. Staging's ledger lists only `20261016094050_staging_doka_core_schema_rls_storage` and `20261017081123_doka_rpc_security_hardening`. This divergence is material: **freeze database pushes** until the ledger reconciliation is explicitly verified.
> - PR [#90](https://github.com/logixaflow-commits/doka-ai-dms/pull/90) is a review candidate stored outside the executable migrations directory. No candidate SQL has been applied to either database.
> - Production Security Advisor reports the known leaked-password-protection plan limitation. No auth settings were changed during this audit.
>
> **Historical migration and RPC reconciliation — 2026-10-17**
>
> - Production project `jkobgssaqifzrqfirdfu` remains ACTIVE_HEALTHY. On 2026-10-17, `20261017170027_doka_rpc_security_hardening` was briefly applied, then compensated by `20261017170133_rollback_doka_rpc_security_hardening` because the repository's staging HTTP lifecycle/A-B prerequisite had not been met. No document rows or storage objects were changed.
> - Production's four sensitive RPCs are back to `SECURITY INVOKER`; `authenticated` can execute them, while `anon` and `service_role` cannot. `authenticated` cannot create objects in `public`. Production Security Advisor now reports the known leaked-password-protection warning only.
> - **Important unresolved runtime risk:** production column grants intentionally deny direct updates to storage-pointer fields, while the RPCs are back to `SECURITY INVOKER`. Version replacement/restore paths that update protected columns may fail at runtime. Authenticated UPDATE grants do include `status` and `deleted_at`, so bulk status/trash have the required column privileges but still require authenticated HTTP acceptance. Do not claim those workflows are accepted until the staging authenticated HTTP lifecycle and two-user isolation gates pass and a reviewed forward migration is approved.
> - The hardening candidate is kept at `20261017170027_doka_rpc_security_hardening.sql` to match the production migration ledger. Staging still records the equivalent hardening under legacy version `20261017081123`. The production-only rollback SQL is under `supabase/production-rollback/` deliberately, so a normal staging migration push cannot undo staging's test setup. **Freeze database pushes until the staging/production migration-ledger divergence is reconciled.**
> - Staging project `gzxybtqquzycogaowdbj` remains ACTIVE_HEALTHY with the four owner-checked `SECURITY DEFINER` RPCs. The generic authenticated-callable SECURITY DEFINER warning must be reviewed against fixed search paths, owner checks, restricted EXECUTE grants and real A/B evidence.
> - Production Security Advisor's leaked-password-protection warning remains; the current Supabase plan does not expose the HaveIBeenPwned-based control. Do not describe this warning as fixed.
>
> ---

> **Owner:** How is Doka's database, migration, ownership and RLS boundary maintained?
> **Update when:** Schema, migration heads, RLS, RPC/function privileges, ownership checks or database providers change.
> **Last Updated:** 2026-10-21
> **Do NOT put here:** Release-gate status, deployment credentials, or provider-specific recovery runbooks.

## Current authority
Personal Local uses local application state where configured. Personal Cloud uses Supabase Postgres as the current metadata/authz data boundary.

## Historical verification — 2026-10-08 (superseded by the live checkpoint above)
- Supabase project: Enterprise AI DMS
- Project ref: jkobgssaqifzrqfirdfu
- Status: ACTIVE_HEALTHY
- PostgreSQL: 17.6.1
- Latest live migration: 20261005113241_doka_audit_export_backup_actions

## Security model
Backend/Worker owns database access. Browser code must never receive service-role credentials. RLS is defense-in-depth and does not replace API authorization. Owner checks must be performed from the authenticated identity.

## Migrations
Schema changes use the repository's migration system. Prefer forward corrective migrations over destructive downgrade. Repository head and live production head are separate facts.

Repository hardening candidate: `20261017170027_doka_rpc_security_hardening.sql` (staging acceptance candidate).
Production migration ledger: `20261017170027_doka_rpc_security_hardening` followed by `20261017170133_rollback_doka_rpc_security_hardening`.

The staging ledger still uses legacy version `20261017081123`; migration-ledger reconciliation is required before any automated database push.

## Cloud controls
Doka document/version tables use owner-scoped RLS. Version pointer functions require authenticated owner validation. Bulk mutations are atomic and owner-scoped.

Live database health and migration state do not close Gate 10. Two real authenticated users must still demonstrate cross-user API/RLS/Storage denial and owner-scoped access.

## Deferred database material
D1/Turso migration material is future/deferred architecture, not current production database authority. Do not dual-write or switch the active Worker without staging, isolation, rollback and remote integration evidence.
