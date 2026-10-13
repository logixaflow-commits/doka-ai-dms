# Doka Deployment

> **Owner:** Where does Doka run and what deployment evidence is required?
> **Update when:** Runtime topology, Worker deployment, hosting provider state, migration evidence or release prerequisites change.
> **Last Updated:** 2026-10-13
> **Do NOT put here:** Application architecture detail, secrets, or detailed incident procedures.

## Active topology
- Personal Local: FastAPI + React/Vite on the user's machine.
- Personal Cloud API: Cloudflare Worker doka-ai-dms.
- Supabase: Auth, Postgres/RLS and private Storage.
- Vercel: project is inactive in the connected account; explicit paused-state field is not exposed by the connected API, so owner-paused remains VERIFY.
- Render: the connected `My Workspace` service-list requests returned `null` on 2026-10-09 (with preview services both enabled and disabled); no service ID/configuration was visible to inspect. This is a connector visibility result, not proof that no service exists elsewhere. The repository contains Railway configuration files, but no evidence confirms Railway is the active runtime.

## Cloudflare Worker
Current URL: https://doka-ai-dms.logixaflow.workers.dev.

Live verification on 2026-10-13:
- Worker: doka-ai-dms
- Current traffic: 100% on the latest inspected deployment.
- Latest deployment ID: `d894b59e-4aca-4fa2-86b2-9750055749eb` (created 2026-10-13T07:02:03Z).
- Active version ID: `75e436b2-2009-4779-b659-5421bea0843a`.
- Deployment path: `.github/workflows/cloudflare-worker-deploy.yml` is the retained pinned, dry-run, explicit-confirmation deployment path. No production deployment was triggered during this review.
- Live CORS contract: explicit release/preview origins only with `allow_credentials=False`; the legacy `enterprise-ai-dms.vercel.app` origin is no longer present in the live bundle.

The Worker must authenticate cloud requests and must not proxy large document bytes unnecessarily. Direct upload sessions are used for provider-backed document bytes. A dedicated `DOKA_STORAGE_SESSION_SECRET` is now provisioned as a Worker secret; `DOKA_SINGLE_USER_EMAIL` remains intentionally enabled for the current single-user deployment.

The per-user B2 quota is now configured as Worker secret binding `B2_QUOTA_BYTES=1073741824` (1 GiB/user). The quota evaluator warns at 80% projected usage and blocks new B2 uploads at 95%; this is configuration/deployment evidence only, not proof of a successful live B2 upload, quota rejection, or recovery test.

## Vercel
Connected Vercel project: enterprise-ai-dms.
Current observed state: live=false. Latest production deployment state: CANCELED.
The connected API did not expose an explicit paused-state property. Do not upgrade the historical owner-paused statement to VERIFIED without explicit dashboard/API evidence.

## Render
The connected `My Workspace` service-list requests returned `null` on 2026-10-09, even with previews enabled. No service ID or environment configuration was returned, so the connected account view cannot currently support a safe Render change/deploy. Confirm the intended service in the Render Dashboard before adding secrets or deploying. Repository `infrastructure/railway/*` files are not proof that Railway is active and must not be used as the runtime authority without owner confirmation.

## Release evidence
Required before production sign-off: authenticated user lifecycle, two-user isolation, 50 MiB boundary, provider recovery drills, OCR benchmark, backup/recovery proof, Supabase security settings, and runtime monitoring evidence. D1 authorization-integrity migration 0002 has now been applied after a successful pre-change export/restore check; its seven expected index/trigger objects were verified in production and the affected metadata tables remain empty. The active document API still uses Supabase Postgres/Storage; D1 guard installation is not a substitute for Supabase RLS or two-user acceptance. Gate 9/10 execution uses the current direct-upload session/completion API and verifies actual downloaded bytes against SHA-256; it requires two pre-created user access tokens and an exact 50 MiB fixture for full closure. The runner must execute against a dedicated acceptance environment that allows both test users; production single-user restriction must not be weakened just to make the test pass. Gate 11 additionally requires live B2 and Google Drive recovery evidence and a real Cloudinary application-path check.

### Latest live acceptance checkpoint — 2026-10-13
A read-only query of the active Supabase project returned 0 rows in each of `public.doka_documents`, `public.doka_document_versions`, and `public.doka_audit_events`. Therefore, no document lifecycle is evidenced in these tables at this checkpoint, and authenticated upload/download, two-user isolation, version history, and audit-event acceptance remain unproven. Do not infer success from empty tables or from unauthenticated endpoints returning 401.

Supabase performance advisors reported three currently unused indexes: `doka_audit_events_owner_created_idx`, `doka_documents_storage_provider_idx`, and `doka_document_versions_storage_provider_idx`. These were not removed because the document tables are empty at this checkpoint; collect representative workload evidence before considering index removal.

The OCR acceptance report at `docs/Report/ocr-benchmark.json` remains `gate_ready: false`. Its strict quality gate (CER <= 10%, WER <= 20%) records six threshold violations across three samples; the threshold must not be relaxed to make the gate pass. Existing exploratory sample sets are explicitly not acceptance evidence because reference provenance/source alignment is incomplete.

The latest code commit's connector-visible commit status only reported a successful Vercel check; the workflow-run lookup returned no PR-triggered runs for that SHA. This is not proof that the GitHub Actions backend suite passed. Verify the current GitHub Actions run before release sign-off.

## Authenticated provider acceptance checkpoint — 2026-10-13

Fresh read-only checks against the connected Cloudflare and Supabase accounts:
- The active Worker has secret bindings for all four B2 connection fields, the B2 quota, the dedicated storage-session signer, and all four Google Drive OAuth/folder fields. Cloudflare's API only exposes secret binding names/types here; this does not prove that B2 credentials are accepted by Backblaze or that Google OAuth refresh succeeds.
- The Worker subdomain is enabled, and the latest inspected deployment still serves 100% traffic. The runtime retains `DOKA_SINGLE_USER_EMAIL`; do not disable this production restriction to make a two-user test pass.
- The configured application object-size boundary is 52,428,800 bytes (50 MiB). Source uploads at or below the boundary route to Supabase; source uploads above it route to B2 and invoke the per-user quota check.
- Supabase currently has two Auth users and one Storage bucket; the `doka-documents` bucket has zero objects. The three Doka metadata tables (`doka_documents`, `doka_document_versions`, `doka_audit_events`) each have zero rows.
- Read-only RLS policy inspection shows owner-scoped authenticated policies for Doka documents, document versions, audit events, and objects under the `users/<auth.uid()>/...` path in `doka-documents`. This is policy evidence, not a substitute for live cross-user requests.

A single-user live provider runner is available at `scripts/cloud_provider_acceptance.py`. It exercises an authenticated source upload/download with SHA-256 verification, version replacement/history, Google Drive export session and completion verification, lifecycle audit events, trash/restore, and cleanup. Use `--provider b2` to upload a fixture larger than 50 MiB through the B2 route; the test then replaces it with a small Supabase-backed version before Drive export to avoid uploading a second large object. Use `--provider supabase` for the Supabase source path.

The runner requires `DOKA_CLOUD_BASE_URL`, `DOKA_CLOUD_USER_TOKEN`, and an output path. Never put access tokens in source control or chat. The live run has **not** been executed because a valid user session token is not available in the connected tools. The two-user runner (`scripts/cloud_acceptance.py`) additionally requires two distinct test-user tokens and an acceptance environment that permits both users; production's single-user guard must remain enabled.

## Database migration distinction
Repository migration includes the reconciled least-privilege trigger migration `20261009083942_doka_trigger_function_least_privilege`.
Last verified live Supabase head on 2026-10-09: `20261009083942_doka_trigger_function_least_privilege`.
These are separate facts; live state requires fresh verification before release.

## Deferred deployment references
Historical Render/FastAPI-cloud deployment instructions and older cloud-first architecture are preserved in archive/legacy. They are not current deployment authority.
