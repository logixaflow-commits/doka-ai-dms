# Staging Infrastructure Checkpoint — 2026-10-16

## Safety boundary

- Production Supabase project `Enterprise AI DMS` (`jkobgssaqifzrqfirdfu`) remains `ACTIVE_HEALTHY`. It was not paused, deleted, migrated, or used for acceptance writes.
- Production Cloudflare Worker `doka-ai-dms` and D1 database `doka-ai-dms-prod` were not changed.
- No paid Supabase plan, paid project, or Supabase development branch was created.
- Never point acceptance tests at the production Worker or production Supabase project.

## Free staging resources created

| Resource | Identifier | Status |
|---|---|---|
| Supabase staging | `doka-ai-dms-staging` / ref `gzxybtqquzycogaowdbj` | `ACTIVE_HEALTHY` |
| Cloudflare D1 staging | `doka-ai-dms-staging` / UUID `11baa497-e6f7-4054-8e9f-3a21baec93f3` | Created, APAC |
| Supabase project creation quote | Enterprise AI DMS organization | $0/month |

Supabase staging region is `ap-southeast-1`. The project was created only after the cost API returned $0/month and the zero-cost confirmation was obtained.

## Staging schema setup

- Supabase staging has `public.doka_documents`, `public.doka_document_versions`, and `public.doka_audit_events`.
- RLS is enabled on all three tables.
- Owner-scoped authenticated policies are installed for document select/insert/update and soft-delete-aware permanent delete; versions are scoped through their parent document; audit events are owner-scoped and insert/select only.
- Private Storage bucket `doka-documents` exists with a 52,428,800-byte (50 MiB) limit.
- Storage object policies constrain select/insert/delete to `users/<auth.uid()>/...` in that bucket.
- Staging Supabase Security Advisor returned no security lints after the setup.
- The schema was initialized from read-only inspection of production table columns, constraints and policy definitions. **Before release, reconcile this bootstrap SQL against the repository's canonical migration history and verify all RPCs/triggers expected by the current Worker.** Do not infer complete application compatibility from table presence alone.

Cloudflare D1 staging has a schema-only initialization with the observed Doka tables, indexes and integrity triggers. No production rows or secrets were copied. It currently has 11 tables, 13 indexes and 10 triggers.

## Still blocked / pending evidence

1. Deploy a dedicated `doka-ai-dms-staging` Worker with bindings to staging D1 and staging Supabase only. Do not reuse production credentials or production bindings.
2. Provision two distinct disposable Supabase Auth users in staging and obtain their access JWTs using a secure local workflow. Never put tokens in Git, logs, or chat.
3. Run live health/config and CORS checks against the staging Worker.
4. Run authenticated upload/download, SHA-256 byte-integrity, exact 50 MiB boundary, versioning, trash/restore, cleanup, and User A/User B cross-user isolation tests against staging only.
5. Run B2, Cloudinary and Google Drive application-path recovery tests only when separate staging-safe credentials/folders are available. Production credentials must not be used as staging test credentials.
6. Run a fresh Myanmar (`mya`) and English (`eng`) OCR benchmark and local backup/restore browser acceptance with reproducible evidence.
7. Confirm exact-HEAD GitHub CI/CodeQL and preview-only Vercel smoke evidence. Keep Vercel production manual-only; do not reactivate or promote production without explicit release approval.
8. Render `My Workspace` returned no service records through the connected account. Do not create a replacement service without confirming the intended Render runtime.

## Verification rule

Resource creation and schema/policy configuration are not live acceptance. Keep release status BLOCKED until all required tests above have fresh, scrubbed evidence and the exact candidate SHA passes its required checks.
