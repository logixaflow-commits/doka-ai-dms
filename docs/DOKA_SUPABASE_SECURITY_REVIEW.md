# Doka Supabase Security Review — Source-Level Findings

Review date: 2026-10-03  
Scope: repository migration source under `supabase/migrations/` and the Cloudflare Worker data-access contract.  
Status: **source review only**. This document does not prove that migrations are applied to a live Supabase project, that effective grants match the repository, or that cross-user tests have passed.

## Observed controls in migration order

### Document metadata

- `doka_documents` has RLS enabled.
- Owner-scoped SELECT, INSERT and UPDATE policies compare the row owner to `auth.uid()`.
- The general owner DELETE policy is removed by the least-privilege migration.
- The later permanent-delete migration grants DELETE back only with an RLS policy requiring both matching `auth.uid()` and `deleted_at IS NOT NULL`.
- Authenticated UPDATE privileges are narrowed to `status`, `metadata`, then extended by the lifecycle migration to `filename`, `folder_path` and `deleted_at`. Storage pointer columns such as `object_key`, `sha256` and `size_bytes` are not granted for direct client updates.

### Storage

- The `doka-documents` bucket is configured private with a 50 MiB object limit.
- Storage object policies scope SELECT, INSERT and DELETE to `users/<auth.uid()>/...`.
- An earlier owner-scoped UPDATE policy is explicitly dropped by `20261001100500_doka_storage_no_overwrite_policy.sql`, consistent with uploads using `x-upsert=false`.
- Effective bucket limits, grants and policies still require live-project inspection.

### Version history and privileged RPCs

- Version rows inherit owner scope through the parent document in RLS.
- The append-only migration revokes authenticated DELETE on version history.
- Version replacement and restore use narrowly granted SECURITY DEFINER functions with fixed search paths, explicit authentication/ownership checks, and validation of SHA-bound object keys and metadata.
- The migration chain includes multiple successive hardening revisions; verify the final definitions in the live database rather than assuming every migration has been applied in order.

### Audit events

- Audit events have owner-scoped SELECT and INSERT RLS policies and authenticated SELECT/INSERT grants only.
- The Worker writes audit events best-effort and catches failures. Therefore, current code does **not** guarantee an audit row for every successful business operation; stronger audit guarantees need a transactional database-side design.
- Document deletion uses `ON DELETE SET NULL` for the audit document reference so an event can remain after permanent deletion.

## Remaining live verification

Do not mark SEC-011 complete until an authorized reviewer verifies the live project:

- Confirm all migrations are applied and inspect effective grants for `anon`, `authenticated` and `service_role`.
- Query `pg_policies` for `public.doka_documents`, `public.doka_document_versions`, `public.doka_audit_events` and `storage.objects`.
- Verify the private bucket and 50 MiB size limit in `storage.buckets`.
- Use two independent authenticated test users to verify cross-user SELECT/UPDATE/DELETE and Storage read/write attempts are denied.
- Verify user A cannot call version RPCs against user B's document or object key.
- Verify authenticated clients cannot update `object_key`, `sha256` or `size_bytes` directly and cannot delete version-history rows.
- Verify audit events are owner-isolated and assess whether best-effort audit writes meet the product's evidence requirements.

## Phase 3 security automation status

- CodeQL analysis is configured in the consolidated quality workflow for Python and JavaScript/TypeScript.
- Semgrep runs as a report-only baseline and uploads SARIF; findings need triage before turning it into a blocking gate.
- Syft generates an SPDX JSON SBOM artifact per quality workflow run.
- OWASP ZAP DAST is not pointed at production: Vercel production remains paused, and no approved staging URL/environment is currently configured. Add DAST only after a dedicated staging target and safe test credentials exist.
- GitHub branch-protection/ruleset enforcement of code-scanning findings must be verified separately; workflow upload alone does not prove PR blocking.
