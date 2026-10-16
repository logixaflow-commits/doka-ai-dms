> **Production-readiness checkpoint — 2026-10-16 (post PR #64)**
>
> - Latest `main` HEAD is `94f95b683f62b651f6bb9d959265bf812c28d174`; PR [#64](https://github.com/logixaflow-commits/doka-ai-dms/pull/64) merged after all applicable checks passed. The main-branch CI and quality workflows for this documentation-only merge were still running at the latest check; verify the exact-HEAD run before calling it green.
> - The latest confirmed production deployment is Vercel `READY` for main SHA `2893c82ba1386969b6f6b86df2189b26f0e84b26`; the canonical frontend URL returned HTTP 200 for the HTML shell. Authenticated user workflows are not yet verified for the new main SHA.
> - Supabase staging creation remains blocked: the project quote was $0/month, but creation was rejected by the organization’s active-free-project limit. Supabase branch pricing returned $0.01344/hour, so no branch was created. No paid resource, project deletion, pause, or plan upgrade was performed.
> - The only Supabase project returned for this organization is production `jkobgssaqifzrqfirdfu`. It must not be used for destructive acceptance tests. Security Advisor still warns that leaked-password protection is disabled.
> - Cloudflare Worker `doka-ai-dms` is production, uses production D1/Supabase bindings, and must not be used for acceptance tests. Render `My Workspace` has no services. No staging resources were created.
> - The authenticated acceptance runner now rejects the known production Worker host at the script level as well as in GitHub Actions; unit tests cover production rejection, HTTPS validation, and a non-production URL.
> - **Release blockers:** isolated staging Supabase/storage + Worker/D1, disposable distinct User A/B tokens, authenticated lifecycle/download-integrity/50 MiB/cross-user-isolation evidence, provider recovery tests, and fresh Myanmar/English OCR + local recovery validation. Do not mark production-ready until these are complete.
>
> ---
>

> **Live verification checkpoint — 2026-10-16 08:45 UTC**
>
> - Latest `main` HEAD checked: `ca9b18c539773e2af760fd987f8c184771069ab4`.
> - Exact-HEAD [Production CI/CD](https://github.com/logixaflow-commits/doka-ai-dms/actions/runs/38874722614) and [Doka Quality Checks](https://github.com/logixaflow-commits/doka-ai-dms/actions/runs/38874722613) both **passed**. The check-runs API reports Production Release Gate, Supabase Preview, dependency audits, frontend build/smoke tests, backend regression/lint/tests, storage contract tests, workflow sanity, symlink security, and SBOM/static analysis all successful.
> - Vercel production deployment for current `main` commit `ca9b18c539773e2af760fd987f8c184771069ab4` is `READY` (`enterprise-ai-if74grehv-logixaflow-9859.vercel.app`); HTTP smoke test of [https://enterprise-ai-dms.vercel.app](https://enterprise-ai-dms.vercel.app) returned **200 OK** and the Doka HTML shell. This verifies delivery of the frontend shell only, not authenticated application workflows.
> - Render `My Workspace` service listing returned no services. Do not claim a Render backend is deployed unless a service is intentionally created and configured.
> - Cloudflare account lists only Worker `doka-ai-dms` and D1 database `doka-ai-dms-prod`; its secret inventory contains provider credentials and Supabase publishable key, but secret values were not read. No staging Worker or isolated D1 was created.
> - Supabase project `jkobgssaqifzrqfirdfu` is `ACTIVE_HEALTHY`; Security Advisor still reports leaked-password protection disabled (plan limitation previously reported by the user). No database changes were made.
> - The authenticated cloud acceptance run still failed before lifecycle/isolation checks. **Do not run it against production.** Release blockers remain: an isolated staging Supabase project/storage and Worker, disposable User A/B tokens, full authenticated upload/download/50 MiB/isolation evidence, provider recovery tests, and fresh Myanmar/English OCR + local recovery validation. Keep production single-user restrictions and do not mark production-ready until these pass.
>
> ---
>
> **Production deployment checkpoint — 2026-10-16 08:32 UTC**
>
> - Current `main` HEAD: `d3eba2f4ca14e1c99144f3e26e75a6097064b4b6`. PR [#61](https://github.com/logixaflow-commits/doka-ai-dms/pull/61) was merged. Its fix handles the `any` provider input and rejects the known production Worker hostname as a cloud-acceptance target.
> - Exact-HEAD CI: [Production CI/CD](https://github.com/logixaflow-commits/doka-ai-dms/actions/runs/38874148782) **passed**; [Doka Quality Checks](https://github.com/logixaflow-commits/doka-ai-dms/actions/runs/38874148775) **passed**; [CodeQL](https://github.com/logixaflow-commits/doka-ai-dms/actions/runs/38874148878) was **in progress at audit time**. Recheck before release sign-off.
> - [Authenticated Cloud Acceptance run 38872116178](https://github.com/logixaflow-commits/doka-ai-dms/actions/runs/38872116178) failed at the initial `/health` assertion before lifecycle/isolation checks. This does not identify the exact HTTP status, and does not prove upload/download, 50 MiB, or user-isolation gates.
> - Cloudflare API currently lists one Worker script, `doka-ai-dms`; no dedicated staging script was listed. The repository's root `wrangler.jsonc` binds `DOKA_DB` to database `doka-ai-dms-prod`. Do **not** clone/deploy this config as staging without first creating isolated resources and verifying bindings; never run acceptance against production.
> - Supabase project `jkobgssaqifzrqfirdfu` reports `ACTIVE_HEALTHY` with migrations through `20261009083942_doka_trigger_function_least_privilege`. Security advisor still warns that leaked-password protection is disabled (known plan limitation); performance advisor reports three unused indexes, informational only. No schema, data, secrets, routing, or production settings were changed in this audit.
> - Remaining P0 gates: dedicated isolated acceptance Worker/resources + disposable User A/B access JWTs; authenticated lifecycle and exact 50 MiB byte/hash verification; real two-user API/RLS/Storage/RPC isolation; B2/Cloudinary/Google Drive app-path recovery; fresh browser-based Myanmar/English OCR benchmark and local recovery evidence; confirm Vercel production deployment/live status and intended Render service. Keep production single-user restrictions; do not mark production-ready until evidence passes.
>
> ---
>
> **Production release checkpoint — 2026-10-16 (after Vercel root-directory repair)**
>
> - Current repository `main` HEAD: `72ade0e5abc7a43f018a1165689bf1ff4255db6c`. Production CI/CD, Doka Quality Checks and CodeQL passed for this commit: [Production CI](https://github.com/logixaflow-commits/doka-ai-dms/actions/runs/38851617374), [Quality Checks](https://github.com/logixaflow-commits/doka-ai-dms/actions/runs/38851617562), [CodeQL](https://github.com/logixaflow-commits/doka-ai-dms/actions/runs/38851617443).
> - Vercel project `enterprise-ai-dms`: the previous deployment failed because Root Directory was configured as `web-platform/frontend`, which no longer exists. Project Root Directory was corrected to `apps/web-platform/frontend`, and the ignored-build-step command was reset to the default/null setting.
> - A fresh preview deployment and a fresh production deployment for the same `main` SHA both reached `READY`. Production deployment: [deployment details](https://vercel.com/logixaflow-9859/enterprise-ai-dms/GL4VFqatCW29koYZMhCb84tM3RV8). Its aliases include `https://enterprise-ai-dms.vercel.app`. Vercel project API still reports `live=false`; canonical-alias HTTP smoke could not be independently confirmed by the available web/runtime network, so do not claim the whole application is fully live solely from build status.
> - **Release remains partial, not full go-live.** Authenticated upload/download/version/audit lifecycle, two-user isolation, real B2/Google Drive/Cloudinary application-path recovery and a strict Myanmar/English OCR benchmark remain open. Run cloud acceptance only with disposable users in a dedicated acceptance environment. Do not weaken the production single-user restriction.
> - Required owner input for cloud acceptance: add `DOKA_CLOUD_BASE_URL`, `DOKA_CLOUD_USER_A_TOKEN`, and `DOKA_CLOUD_USER_B_TOKEN` as GitHub Actions secrets/variables. A/B values must be distinct Supabase test-user **access JWTs**, not UUIDs. Never send tokens in chat.
> - OCR branch review: the current `apps/web-platform/backend` OCR code/tests and current `.github/workflows/myanmar-ocr-regression.yml` contain the useful Myanmar identifier/numeral, Unicode normalization, original-image fallback, PDFium fallback and safety-limit regressions. The old branch's Google Drive digest-property assertion is not safe to port because current main verifies the actual object bytes. The branch is stale/diverged and should be deleted only after the owner confirms no uncommitted/unique work is needed.
>
> ---
>
> **Production checkpoint — 2026-10-15 10:10 UTC (fresh verification)**
>
> - Cloudflare Worker deploy [run 38706138555](https://github.com/logixaflow-commits/doka-ai-dms/actions/runs/38706138555) and live infrastructure smoke [run 38706261696](https://github.com/logixaflow-commits/doka-ai-dms/actions/runs/38706261696): **success**. Health/config return HTTP 200, unauthenticated document listing returns HTTP 401, trusted CORS passes and an untrusted origin is denied.
> - Doka Quality Checks on the latest docs HEAD [run 38707844647](https://github.com/logixaflow-commits/doka-ai-dms/actions/runs/38707844647): **success**. CodeQL also passed on the Worker release commit.
> - Canonical Vercel alias https://enterprise-ai-dms.vercel.app returned HTTP 200 and the expected `Doka — Secure Document Workspace` title on 2026-10-15. This confirms basic page availability only.
> - Vercel project `enterprise-ai-dms` reports `live=false`. Recent production deployment attempts for `main` (including commit `4ce4036`) are `CANCELED`; the deployment API points to the **Ignored Build Step** configuration. The workflow explicitly says Vercel production is paused/manual-only. Do not silently change that setting or promote a deployment; owner must explicitly approve re-enabling production deployments. Latest READY deployment remains commit `1dd3ace`, so current frontend source publication is not yet proven.
> - Full cloud release is **not signed off**: authenticated upload/download/version/audit lifecycle, two-user isolation, real B2 / Google Drive / Cloudinary recovery, strict Myanmar/English OCR benchmark and recovery evidence remain open. Use disposable users and a dedicated acceptance environment; never disable `DOKA_SINGLE_USER_EMAIL` on production to make tests pass.
>
> ---
>
> **Cloudflare deployment follow-up — 2026-10-15**
>
> Direct deployment/version API confirms latest listed Worker deployment `d894b59e-4aca-4fa2-86b2-9750055749eb`, version 724 (`75e436b2-2009-4779-b659-5421bea0843a`), at 100% traffic. The account currently lists zero zones and no custom Worker domains. This verifies the deployment traffic assignment only; it does not verify external health, custom-domain routing, secrets, CORS in a real browser, or provider application-path recovery.

---

> **Live provider inventory — 2026-10-15 (read-only API inspection)**
>
> - GitHub `main` latest observed SHA: `6c1fe995c807382cbe3c1000e893e678d621f83b`; confirm CI against this exact SHA.
> - Vercel `enterprise-ai-dms`: `live=false`; latest production deployment for this SHA is `CANCELED`. Production remains paused/manual-only pending explicit owner approval and gates 9–11.
> - Render `My Workspace` service listing returned `null`, including previews. This is not proof that no service exists in other workspaces/accounts. Owner must confirm the target; do not create a guessed replacement.
> - Supabase `Enterprise AI DMS` ref `jkobgssaqifzrqfirdfu`: `ACTIVE_HEALTHY`, `ap-southeast-1`, Postgres 17. Latest listed migration: `20261009083942_doka_trigger_function_least_privilege`. Two-user API/Storage acceptance remains open.
> - Cloudflare account lists zero zones. Worker script `doka-ai-dms` exists, but the script-list endpoint returned `routes: null` and empty `deployment_id`. Inspect current deployments, versions, routes/custom domain and health before relying on older 100%-traffic notes.
> - No deployment, traffic, DNS, secrets, database schema or data mutation was performed. Detailed inventory: [REPOSITORY_INFRA_AUDIT_2026-10-15.md](REPOSITORY_INFRA_AUDIT_2026-10-15.md).

---

# Doka Deployment

> **Owner:** Where does Doka run and what deployment evidence is required?
> **Update when:** Runtime topology, Worker deployment, hosting provider state, migration evidence or release prerequisites change.
> **Last Updated:** 2026-10-13 (updated after deployment workflow attempts)
> **Do NOT put here:** Application architecture detail, secrets, or detailed incident procedures.

## Active topology
- Personal Local: FastAPI + React/Vite on the user's machine.
- Personal Cloud API: Cloudflare Worker doka-ai-dms.
- Supabase: Auth, Postgres/RLS and private Storage.
- Vercel: project is inactive in the connected account; explicit paused-state field is not exposed by the connected API, so owner-paused remains VERIFY.
- Render: the connected `My Workspace` service-list requests returned `null` on 2026-10-09 (with preview services both enabled and disabled); no service ID/configuration was visible to inspect. This is a connector visibility result, not proof that no service exists elsewhere. The repository contains Railway configuration files, but no evidence confirms Railway is the active runtime.

## Cloudflare Worker
Current URL: https://doka-ai-dms.logixaflow.workers.dev.

### Live checkpoint — 2026-10-14 (read-only)

- `GET /health` and `GET /api/config` both returned HTTP 200. The public config reports Supabase Auth and the document bucket as configured; this is readiness evidence, not a provider transaction.
- Unauthenticated requests to `/api/documents`, `/api/folders`, and `/api/audit` returned HTTP 401. A deliberately invalid bearer token also returned HTTP 401 on all three routes. No document data was created or changed.
- CORS preflight returned HTTP 200 for the two existing release/preview origins, but HTTP 400 `Disallowed CORS origin` for the owner-provided `https://enterprise-ai-b3vo95b6b-logixaflow-9859.vercel.app` origin.
- PR #48 adds that exact origin to the Worker's explicit fallback allowlist and was merged as `65436a2309c9f2e63214841fc7ad41e944f87579`. Doka Quality Checks and CodeQL passed on that merge SHA.
- The latest live Worker deployment remains `d894b59e-4aca-4fa2-86b2-9750055749eb`, version `75e436b2-2009-4779-b659-5421bea0843a`, at 100% traffic (created 2026-10-13T07:02:03Z). The new CORS allowlist change is **not live yet**; the merge's production-deploy workflow was skipped because no explicit `[deploy-worker]` release marker was supplied.
- Production deployment remains gated. The previous deploy attempt failed Cloudflare API authentication (`10000`); the owner must correct the GitHub `CLOUDFLARE_API_TOKEN`/account scope and explicitly authorize the gated deployment before the live preflight can be re-tested. Do not weaken the production single-user restriction to complete test gates.


Live verification on 2026-10-13:
- Worker: doka-ai-dms
- Current traffic: 100% on the latest inspected deployment.
- Latest deployment ID: `d894b59e-4aca-4fa2-86b2-9750055749eb` (created 2026-10-13T07:02:03Z).
- Active version ID: `75e436b2-2009-4779-b659-5421bea0843a`.
- Deployment path: `.github/workflows/cloudflare-worker-deploy.yml` retains a dry-run gate and the `[deploy-worker]` explicit release marker. Current main includes the streaming Drive checksum fix and passing quality checks, but the production deployment remains blocked: the build dry-run passed and the actual deploy call returned Cloudflare API authentication error `10000`. The active deployment is still the version listed above.
- Live CORS contract: explicit release/preview origins only with `allow_credentials=False`; the legacy `enterprise-ai-dms.vercel.app` origin is no longer present in the live bundle.

The Worker must authenticate cloud requests and must not proxy large document bytes unnecessarily. Direct upload sessions are used for provider-backed document bytes. A dedicated `DOKA_STORAGE_SESSION_SECRET` is now provisioned as a Worker secret; `DOKA_SINGLE_USER_EMAIL` remains intentionally enabled for the current single-user deployment.

The per-user B2 quota is now configured as Worker secret binding `B2_QUOTA_BYTES=1073741824` (1 GiB/user). The quota evaluator warns at 80% projected usage and blocks new B2 uploads at 95%; this is configuration/deployment evidence only, not proof of a successful live B2 upload, quota rejection, or recovery test.

### Deployment blocker — 2026-10-13

The production workflow's dry-run now passes with `workers-py==1.17.7` and `uv==0.12.3`. The actual deploy request fails against Cloudflare API endpoints with authentication error `10000`; the new Worker version has **not** been deployed. The GitHub Actions secrets exist but the token currently used by the workflow is not accepted for the Worker deployment operation (or does not have the required account scope).

Required owner action:
1. In GitHub, open **Settings → Secrets and variables → Actions → Repository secrets**.
2. Update `CLOUDFLARE_API_TOKEN` with a valid Cloudflare API token scoped to the same account and authorized to edit/deploy Workers scripts. Do not paste the token into chat or commit it.
3. Confirm `CLOUDFLARE_ACCOUNT_ID` is the account that owns `doka-ai-dms`.
4. Re-run **Cloudflare Worker Production Deploy** for the latest `main` commit after the secret is corrected. The workflow will run a dry-run, deploy, and check production health.

No B2, Supabase, or Google Drive credentials were printed or changed as part of this failed deploy attempt. Wrangler config has `keep_vars: true` to preserve dashboard-managed variables.

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

A single-user live provider runner is available at `scripts/cloud_provider_acceptance.py`; `scripts/run-cloud-provider-acceptance.ps1` prompts for the access token without echoing it and runs the selected provider acceptance (`b2`, `supabase`, or `both`) while clearing the token from the PowerShell process environment afterward. It exercises an authenticated source upload/download with SHA-256 verification, version replacement/history, Google Drive export session and completion verification, lifecycle audit events, trash/restore, and cleanup. Use `--provider b2` to upload a fixture larger than 50 MiB through the B2 route; the test then replaces it with a small Supabase-backed version before Drive export to avoid uploading a second large object. Use `--provider supabase` for the Supabase source path.

The runner requires `DOKA_CLOUD_BASE_URL`, `DOKA_CLOUD_USER_TOKEN`, and an output path. On Windows, `scripts/run-cloud-provider-acceptance.ps1 -Provider both` securely prompts for that token and runs B2 + Supabase provider acceptance. For two-user isolation, use `scripts/run-cloud-isolation-acceptance.ps1 -AcceptanceBaseUrl <isolated-acceptance-https-url>`; it securely prompts for both tokens, creates/removes an exact 50 MiB fixture, and refuses the known production Worker URL. Do not disable `DOKA_SINGLE_USER_EMAIL` in production just to run the isolation test. Never put access tokens in source control or chat. The live run has **not** been executed because a valid user session token is not available in the connected tools. The two-user runner (`scripts/cloud_acceptance.py`) additionally requires two distinct test-user tokens and an acceptance environment that permits both users; production's single-user guard must remain enabled.

## Database migration distinction
Repository migration includes the reconciled least-privilege trigger migration `20261009083942_doka_trigger_function_least_privilege`.
Last verified live Supabase head on 2026-10-09: `20261009083942_doka_trigger_function_least_privilege`.
These are separate facts; live state requires fresh verification before release.

## Deferred deployment references
Historical Render/FastAPI-cloud deployment instructions and older cloud-first architecture are preserved in archive/legacy. They are not current deployment authority.
