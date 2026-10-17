# Staging Infrastructure Checkpoint — 2026-10-16

## Latest staging deployment and acceptance status — 2026-10-17

- The dedicated `doka-ai-dms-staging` Worker is now deployed with the staging D1 database and staging Supabase project; the public `/health` and `/api/config` smoke checks pass.
- The staging Worker receives a generated staging-only `DOKA_STORAGE_SESSION_SECRET` at deploy time. The staging publishable key is public by design and configured only in the staging Worker config; production service-role credentials are not used.
- Staging Supabase RPC hardening migration `doka_rpc_security_hardening` was applied to staging only. Metadata confirms fixed search paths and owner checks; no-identity SQL negative tests pass. Production DB has not been changed.
- Automated OPTIONS requests from GitHub Actions return Cloudflare edge error 1010 before reaching the Worker. The deployment workflow records this as inconclusive and separately checks the CORS response header on GET. Real browser preflight remains required.
- Authenticated User A/B tests, exact 50 MiB integrity, lifecycle cleanup, B2/Cloudinary/Google Drive recovery, strict OCR benchmark, full browser acceptance, and measured RTO/RPO are still pending. Gate 12 remains BLOCKED.

---


## Latest staging RPC reconciliation — 2026-10-17
>
> - A read-only live comparison found the staging Supabase schema contains the three Doka tables and owner-scoped RLS, but its original bootstrap migration did not include the four RPCs present in production. Production's live RPC definitions also differ from the repository's earlier hardened migration history, so migration-history presence alone was not accepted as proof of runtime behavior.
> - Branch `fix/staging-rpc-security-parity` adds `apps/web-platform/backend/supabase/migrations/20261017100000_doka_rpc_security_hardening.sql`. The migration was applied to staging only; the four functions now have fixed search paths and explicit `auth.uid()` ownership checks. Read-only metadata verified their security mode and grants; SQL negative checks verified all four reject missing identity.
> - Staging Security Advisor now warns about four SECURITY DEFINER functions exposed to authenticated callers. This is a deliberate tradeoff for protected storage-pointer/soft-delete updates under least-privilege column grants, not a warning to ignore: the owner checks need authenticated two-user lifecycle/isolation tests before release.
> - The staging Worker is still not deployed. Do not promote this migration to production until the staging Worker and User A/B acceptance runs pass and a rollback plan is confirmed. Gate 12 remains BLOCKED.
>
> ---
>

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


## Latest connected-account recheck — 2026-10-16

- Read-only Supabase inventory confirms exactly two projects in the `Enterprise AI DMS` organization: production `jkobgssaqifzrqfirdfu` and staging `gzxybtqquzycogaowdbj`; both currently report `ACTIVE_HEALTHY`. No production project operation was performed.
- Read-only Cloudflare inventory confirms the staging D1 database `11baa497-e6f7-4054-8e9f-3a21baec93f3` exists. A direct `sqlite_master` query returns 11 non-internal tables including Cloudflare's `_cf_KV` table, 13 indexes and 10 triggers; this is 10 application tables plus the Cloudflare internal table. Separate read-only counts show all 10 application tables have zero rows. No staging data was written.
- The Cloudflare account currently lists only the production Worker script `doka-ai-dms`; no `doka-ai-dms-staging` Worker is deployed. Production Worker settings/secrets were not modified or read.
- Render workspace `My Workspace` currently lists no services. Render remains deferred; no service or paid resource was created.
- For commit `ccd4e77e6702ac6b219fcec7b164e4245a3edb64`, Dependency Review completed successfully, while Production CI/CD, Doka Quality Checks and CodeQL were cancelled. Therefore this commit is **not fully CI-verified**; do not infer success from the Vercel status alone.
- Staging Worker deployment remains blocked on repository Actions secrets `CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`, `SUPABASE_STAGING_PUBLISHABLE_KEY`, and `DOKA_STAGING_STORAGE_SESSION_SECRET`, followed by a successful dry-run/deploy and live health/config/CORS checks. The connected tools do not expose a safe way to verify or set GitHub Actions secret values here; no secret values were retrieved.
- User A/B JWTs and staging-safe B2/Google Drive credentials are still needed for authenticated isolation and provider recovery. Production Worker acceptance remains prohibited.
- No production Supabase, D1, Worker, secrets, routing, or Vercel production settings were changed. No paid resource was created.
