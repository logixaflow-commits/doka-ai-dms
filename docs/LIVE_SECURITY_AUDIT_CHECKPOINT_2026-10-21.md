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

- Production: 32 migrations, including `20261017170027_doka_rpc_security_hardening` and `20261017170133_rollback_doka_rpc_security_hardening`.
- Staging: 2 entries, `20261016094050_staging_doka_core_schema_rls_storage` and `20261017081123_doka_rpc_security_hardening`.

Do not reconcile this by blindly replaying migrations, rewriting migration history, or pushing SQL to production. First compare local migration files with both ledgers; determine which staging migrations are represented by the existing baseline; then run the documented authenticated lifecycle and A/B isolation acceptance on disposable staging users/data. Record results and reviewed forward/rollback plans before changing either database.

## Storage review — no changes made

Prior live inventory found the `doka-documents` bucket is private with a 52,428,800-byte (50 MiB) limit. Its bucket-scoped SELECT/INSERT/DELETE policies target authenticated users and `users/<auth.uid()>/...` object paths. The bucket's `allowed_mime_types` is NULL. Global `storage.objects` grants include anon privileges, but the inspected policy inventory did not show an anon policy for this bucket; no bypass was confirmed.

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

1. Complete a read-only inventory of all staging buckets, policies, and upload consumers.
2. Reconcile migration files against the two live ledgers without applying migrations.
3. Run disposable-user authenticated staging HTTP tests for document create/upload/read/version-replace/restore/bulk-status/trash plus cross-user negative cases.
4. Fix only the failures demonstrated by those tests in a reviewed candidate migration; validate rollback and ledger parity.
5. Implement actual receipt OCR only when a safe configured provider boundary and consent requirements are available; keep 501 otherwise.
6. Record exact commit and workflow evidence after each change.
