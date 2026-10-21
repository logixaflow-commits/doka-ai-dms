# Live Security Audit Checkpoint — 2026-10-21

## Scope and evidence

This checkpoint records a read-only follow-up of the current GitHub main head and the connected production/staging Supabase projects. It does not claim successful end-to-end runtime acceptance and does not apply database, storage, credential, or deployment changes.

- Repository: `logixaflow-commits/doka-ai-dms`
- Observed main head: `36e182a2eb44df9c2bf93ea24dbd93debcef3692` ([commit](https://github.com/logixaflow-commits/doka-ai-dms/commit/36e182a2eb44df9c2bf93ea24dbd93debcef3692))
- Exact-commit combined status returned a successful Vercel status. This check alone is not evidence that every workflow or live application path passed.
- Production Supabase project: `jkobgssaqifzrqfirdfu`
- Staging Supabase project: `gzxybtqquzycogaowdbj`

## Current Supabase Security Advisor findings

### Production

The Security Advisor currently reports one warning:

- `auth_leaked_password_protection`: leaked-password protection is disabled on the current plan/configuration. This is not represented as fixed. See [Supabase password security guidance](https://supabase.com/docs/guides/auth/password-security#password-strength-and-leaked-password-protection).

### Staging

The Security Advisor reports four warnings for authenticated users being able to execute `SECURITY DEFINER` RPC functions:

- `doka_bulk_update_documents`
- `doka_replace_document_version`
- `doka_replace_document_version_storage`
- `doka_restore_document_version`

The warning is a review signal, not proof of an authorization bypass. Staging must retain explicit `auth.uid()` owner checks, fixed `search_path`, strict argument/object-key validation, and least-privilege EXECUTE grants. Verify both allowed owner actions and cross-user denials using disposable authenticated users before deciding whether to retain or change the execution model. Do not suppress the warning without evidence.

## Migration-ledger divergence — database pushes remain frozen

Read-only migration inventory returned:

- Production: **33** ledger entries (not 32), including `20261017170027_doka_rpc_security_hardening` and `20261017170133_rollback_doka_rpc_security_hardening`.
- Staging: **2** entries, `20261016094050_staging_doka_core_schema_rls_storage` and `20261017081123_doka_rpc_security_hardening`.
- Repository `main` contains **30** SQL files under `apps/web-platform/backend/supabase/migrations/`, plus a rollback SQL file under `apps/web-platform/backend/supabase/production-rollback/`.
- Three production-ledger versions do not have a matching SQL file in the main migrations directory: `20261002162812_harden_public_default_privileges`, `20261005071833_revoke_authenticated_version_rpc_execute`, and `20261005073729_doka_version_rpc_execute_hardening`. The rollback ledger entry does exist in the separate `production-rollback/` directory. The repository instead has `20261005090000_doka_version_rpc_execute_hardening.sql`, whose version differs from the production ledger's `20261005073729` entry. This is a concrete migration-history/source-of-truth mismatch that needs reconciliation.
- Neither of the two staging ledger versions matches a versioned SQL file in the main migrations directory, suggesting staging uses a baseline/squashed history that must be explained by its deployment records.

Do not reconcile this by blindly replaying migrations, rewriting migration history, or pushing SQL to production. First establish the intended baseline and the provenance of the three absent production migrations, compare their effects to current schema/functions/grants, and document a forward/rollback plan. Then run the authenticated lifecycle and A/B isolation acceptance on disposable staging users/data. Record results before changing either database.

## Storage review — no changes made

Read-only staging inventory found one bucket: `doka-documents`, private, `file_size_limit=52,428,800` bytes (50 MiB), `allowed_mime_types=NULL`. The staging policy inventory returned three bucket-scoped Storage policies—SELECT, INSERT, DELETE—restricted to `authenticated` and `users/<auth.uid()>/...` object paths, plus owner-scoped RLS policies on `doka_documents`, `doka_document_versions`, and `doka_audit_events`. No anonymous policy for this bucket was present in the inspected policy inventory; this is not a substitute for runtime anonymous and cross-user negative tests. Global `storage.objects` grants include anon privileges, so retain the staging test gate before changing grants or bucket configuration.

Before changing global grants or bucket configuration:

1. Inventory every bucket, policy, and consumer.
2. Add staging negative tests for anonymous list/read/upload/delete and User A accessing User B paths.
3. Check actual content/signatures and MIME handling across web, signed/direct upload, version replacement, desktop, and mobile paths.
4. Decide whether a bucket MIME allowlist is compatible with every supported document format.
5. Stage and verify changes before any production mutation.

Tracking issue: [#93](https://github.com/logixaflow-commits/doka-ai-dms/issues/93).

## Outstanding backend work

- [Issue #82 — RPC grants and migration history](https://github.com/logixaflow-commits/doka-ai-dms/issues/82): staging authenticated HTTP lifecycle, A/B isolation, migration-ledger reconciliation, verified restore/version-replacement behavior, and rollback evidence are still required. PR [#90](https://github.com/logixaflow-commits/doka-ai-dms/pull/90) remains a candidate only; its SQL has not been applied to either database.
- [Issue #93 — Storage ACL and MIME enforcement](https://github.com/logixaflow-commits/doka-ai-dms/issues/93): full bucket/consumer inventory and staging tests remain required.
- [Issue #95 — Real receipt OCR](https://github.com/logixaflow-commits/doka-ai-dms/issues/95): the endpoint must remain authenticated and unavailable (HTTP 501) until real OCR/vision processing, content-signature validation, verified Myanmar/English fixtures, timeout/error tests, redaction, and audited processing are implemented. Do not restore synthetic success-shaped data.
- [Issue #83 — Telegram document actions](https://github.com/logixaflow-commits/doka-ai-dms/issues/83): mutating actions must remain disabled (HTTP 501) until an owner-authorized domain service, idempotency, audit events, and replay/authorization tests exist.

## Owner constraints and release interpretation

- Historical Hugging Face, Groq, and OpenRouter credential rotation and Gemini assignment review are explicitly skipped by owner instruction. This is not evidence that historical Git-history exposure has been remediated.
- The owner-approved release decision remains **Production Ready — Conditional Sign-Off (Owner-approved launch with explicitly deferred post-launch work)**. The four explicitly deferred gates remain: staging synthetic A/B isolation, Myanmar/English OCR CER optimization, secondary staging disaster-recovery drills, and real-browser copied-office-dataset acceptance.
- Do not mark unresolved backend security findings as passed, do not use production for destructive acceptance, and do not apply database/storage changes without staging evidence and review.

## Next execution order

1. Map the only currently observed staging bucket and all three bucket-scoped policies to every upload consumer; run anonymous and cross-user negative tests.
2. Reconcile the 33-entry production ledger, the 2-entry staging ledger, the 30 main migration SQL files, and the separately stored rollback file without applying migrations.
3. Run disposable-user authenticated staging HTTP tests for document create/upload/read/version-replace/restore/bulk-status/trash plus cross-user negative cases.
4. Fix only the failures demonstrated by those tests in a reviewed candidate migration; validate rollback and ledger parity.
5. Implement actual receipt OCR only when a safe configured provider boundary and consent requirements are available; keep 501 otherwise.
6. Record exact commit and workflow evidence after each change.
