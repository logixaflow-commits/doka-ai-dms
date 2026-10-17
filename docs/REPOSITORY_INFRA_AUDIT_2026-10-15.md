> **Latest infrastructure and acceptance checkpoint — 2026-10-17 (supersedes older snapshots below)**
>
> - Latest verified production release SHA: `777b37cc1f443fd367b81e0b38aacd7e1b9f16b9`. Exact-HEAD Doka Quality Checks, Production CI/CD, CodeQL, Dependency Review, desktop Electron smoke and Live Infrastructure Smoke passed.
> - Vercel production deployment is READY on this main SHA. Canonical homepage and production JS asset returned HTTP 200; the production bundle references only production Worker/Supabase, while Preview references only staging Worker/Supabase.
> - Cloudflare production Worker `doka-ai-dms` was redeployed from this SHA. Guarded dry-run/deploy, health/config/single-user smoke and live infrastructure smoke passed. CORS permits the two explicit production origins, does not reflect `https://evil.example`, and unauthenticated document listing returns HTTP 401.
> - Cloudflare also has `doka-ai-dms-staging` and staging D1. Staging Worker settings use only Supabase `gzxybtqquzycogaowdbj`, D1 `11baa497-e6f7-4054-8e9f-3a21baec93f3`, the 50 MiB limit, preview CORS opt-in and a staging-only session secret.
> - Supabase production `jkobgssaqifzrqfirdfu` and staging `gzxybtqquzycogaowdbj` are ACTIVE_HEALTHY. Staging-only RPC hardening is applied and SQL lifecycle/owner-check tests passed transactionally with no fixtures persisted. Production has not received the staging RPC migration.
> - Production Security Advisor still warns that leaked-password protection is disabled due to the current plan. Staging Security Advisor flags four authenticated-callable SECURITY DEFINER RPCs; review the warning alongside fixed search paths, owner checks and real authenticated A/B tests.
> - **Release blockers remain:** authenticated staging User A/B JWTs; HTTP lifecycle and cross-user denial; exact 50 MiB byte/hash integrity; B2/Cloudinary/Google Drive application-path recovery; strict fresh Myanmar/English OCR benchmark; real browser approval/final-copy/backup/isolated restore; measured RTO/RPO; and final security review. Gate 12 remains BLOCKED until all evidence is recorded.
> - Render has no service in the connected workspace and is intentionally not used by the documented Cloudflare Worker cloud runtime. Never run acceptance against production.
> ---
>

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

> **Free-staging recheck — 2026-10-16 (latest; supersedes prior staging availability assumptions)**
>
> - Supabase project creation cost lookup for organization `Enterprise AI DMS` returned **$0/month**. Creation was attempted only with a zero-cost confirmation, but Supabase rejected it because the organization member has reached the maximum of **2 active free projects**. No staging project was created; no project was paused/deleted and no plan was upgraded.
> - Supabase development-branch cost lookup returned **$0.01344/hour**. This is not free, so no database branch was created. Do not use the production project as an acceptance target or bypass the free-project cap with a billable branch.
> - The only listed project in this organization is production project `jkobgssaqifzrqfirdfu` (`ACTIVE_HEALTHY`, `ap-southeast-1`). Live policy inspection shows RLS enabled and owner-scoped policies on `doka_documents`, `doka_document_versions`, `doka_audit_events`, and Storage objects. This is policy-definition evidence only; it is not a substitute for two-user authenticated isolation tests.
> - Supabase Security Advisor still warns that leaked-password protection is disabled; do not represent this as fixed or change the plan. The owner previously reported that HaveIBeenPwned protection requires a paid plan.
> - Latest main commit `2893c82ba1386969b6f6b86df2189b26f0e84b26` has successful Production CI/CD and Doka Quality Checks jobs. The latest Vercel production deployment for that SHA is `READY`, and the deployment HTML shell returned HTTP 200; authenticated workflows remain unverified.
> - Cloudflare Worker `doka-ai-dms` has 100% traffic on its latest listed deployment and is bound to production D1 `doka-ai-dms-prod` plus the production Supabase URL. Secret values were not read. Do not point acceptance tests at this Worker or its production data. Direct external Worker health/CORS probing was not possible from this runtime, so current live health/CORS remains unverified here.
> - **Next safe path:** owner must free an existing free-project slot (after confirming it is safe to pause/delete) or arrange an explicitly approved $0-capable organization. Then create isolated staging Supabase + Worker/D1, configure disposable User A/B JWTs in GitHub secrets, and run lifecycle, exact-50-MiB integrity, cross-user isolation, and provider recovery tests only against staging. Until then, production readiness remains blocked.
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
> **Provider re-audit — 2026-10-16 08:32 UTC**
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
> **Cloudflare follow-up — 2026-10-15**
>
> A direct read of the Worker deployment/version APIs resolves part of the earlier uncertainty: Worker `doka-ai-dms` has latest listed deployment `d894b59e-4aca-4fa2-86b2-9750055749eb` with version `75e436b2-2009-4779-b659-5421bea0843a` (version number 724) assigned **100% traffic**, created 2026-10-13 07:02 UTC. The Worker Domains endpoint returns no custom Worker domains, and the account has zero zones. This confirms a 100%-traffic deployment in Cloudflare's deployment API, but does not prove external health, custom-domain routing, valid secrets or provider application-path success. Keep those checks open.
>
> GitHub combined status for the latest observed code SHA `6c1fe995c807382cbe3c1000e893e678d621f83b` exposes only a successful Vercel context, not Doka Quality Checks/CodeQL/OCR Regression. Exact-SHA CI remains **unverified**. The latest documentation commits likewise expose only the Vercel status context in the checked combined-status API.

---

# Repository and Infrastructure Re-audit — 2026-10-15

## Scope and method

Read-only review of GitHub `main`, canonical release/status documentation, and currently connected Vercel, Render, Supabase, and Cloudflare accounts. This record reports only what the connected APIs exposed. No application deployment, production traffic, secrets, database rows, schema, or provider configuration was changed during this audit.

- Repository: [logixaflow-commits/doka-ai-dms](https://github.com/logixaflow-commits/doka-ai-dms)
- Latest observed `main` commit at audit time: `6c1fe995c807382cbe3c1000e893e678d621f83b` (2026-10-14, UI toast notifications).
- Release rule: green CI or configured credentials alone do not close real-user, OCR, browser, recovery, isolation, or provider acceptance gates.

## Provider findings

### GitHub / repository
- The repository is accessible and the default branch is `main`.
- Canonical documentation exists, including `README.md`, `CURRENT_STATE.md`, `ROADMAP.md`, `PROJECT_OVERVIEW.md`, `TOOL.md`, `docs/OWNER_LOCAL_CHECKLIST.md`, `docs/SELF_AUDIT.md`, `docs/DEPLOYMENT.md`, `docs/OPERATIONS.md`, and `docs/TESTING.md`.
- The latest observed commit is newer than the exact-SHA CI evidence described in older handoff notes. **Do not claim that latest SHA is CI-verified until its own checks are inspected.**
- `fix/myanmar-ocr-text-preservation` was previously recorded as diverged (13 ahead / 120 behind); do not bulk-merge it. Recheck branch status before any reuse.
- The connected GitHub file/search API did not return code-search matches for broad README/TODO queries; that is not proof the repository contains no TODOs.

### Vercel
- Project: `enterprise-ai-dms`; framework `vite`; `live=false`.
- Latest observed production deployment is **CANCELED**, on commit `6c1fe995c807382cbe3c1000e893e678d621f83b`.
- Project domains are listed by the API, but a listed domain is not proof of a successful production response.
- Current posture: keep production paused/manual-only. Do not deploy, change traffic, or reactivate without explicit owner approval and closure of the required cloud gates.
- Next checks: inspect ignored-build-step/cancellation reason, confirm intended deployment protection and environment-variable names (never record values), then run preview-only build/smoke and validate origin/CORS against the deployed Worker. Do not change production as part of these checks.

### Render
- Connected workspace: `My Workspace` (`tea-datqhq0jo6nc73c3qva0`).
- Service listing returned `null` even with preview services included.
- This proves only that no services were returned for this connected workspace through this API call. It does **not** prove there is no service in another workspace/account.
- Next: owner must identify/confirm the intended workspace and service in the Render dashboard. Do not create a replacement or guess a service ID.

### Supabase
- Project: `Enterprise AI DMS`, ref `jkobgssaqifzrqfirdfu`, region `ap-southeast-1`, status `ACTIVE_HEALTHY`, Postgres 17.
- Live migration list includes `20261009083942_doka_trigger_function_least_privilege` as its latest listed migration.
- Prior read-only checks recorded RLS on the Doka document/version/audit tables and `storage.objects`, a private `doka-documents` bucket with a 50 MiB limit, and owner-scoped policies. Those are policy-configuration checks, not proof of two-user API isolation.
- The previously inspected tables/bucket were empty; do not use customer data for acceptance.
- Remaining: use two distinct disposable authenticated users to test document CRUD, Storage signed upload/download, cross-user denial, version/RPC behavior, lifecycle and cleanup. Record privacy-safe evidence only.
- Leaked-password protection remains explicitly deferred under the owner's recorded decision; do not change it silently.

### Cloudflare
- Connected account: `Logixaflow@gmail.com's Account`, ID `71c6a2f23112d7f6b08541c7e1a79ed1`.
- Zone listing returned **zero zones** for this account.
- Worker script `doka-ai-dms` exists; script metadata lists no routes (`routes: null`) and an empty deployment_id in the script-list response. This endpoint alone does not establish active traffic percentage or prove provider health. Earlier documentation records a deployed Worker, so reconcile that historical deployment evidence with the current deployment/route view before calling routing fully verified.
- Next: inspect Worker deployments/versions, routes, custom domain, bindings by name only, logs and health endpoints. Never reveal secret values. Verify CORS for the intended Vercel preview origin and provider application paths with disposable test objects. Do not mutate production routing or secrets during audit.

## Release gates still open

### P0 — Cloud acceptance
- [ ] Confirm exact-`main` CI, CodeQL and OCR regression status for `6c1fe995c807382cbe3c1000e893e678d621f83b`.
- [ ] Gate 9: authenticated user-A lifecycle, including exact 50 MiB boundary, signed upload/download, byte/hash verification, trash/restore/permanent delete, cleanup and privacy-safe evidence.
- [ ] Gate 10: two-user isolation across API, RLS, Storage and RPC using distinct disposable identities; prove user B cannot list/read/download/update user A's resources.
- [ ] Gate 11: live B2 upload/download/delete/recovery and quota boundary; Cloudinary application-path recovery (provider-level probe alone is insufficient); Google Drive export/recovery. Confirm provider selected by the application rather than silently falling back.
- [ ] Reconcile Cloudflare script deployment, active version/traffic, route/custom domain, Worker CORS, bindings and health/log evidence.
- [ ] Confirm the intended Render workspace/service, if Render is still an expected runtime. Do not provision a guessed replacement.
- [ ] Run preview-only Vercel build/smoke and verify environment variable *names/configuration presence* without exposing values; keep production paused.
- [ ] Record fresh Supabase migration, policy, health and disposable-user evidence. No production data reads or destructive changes.

### P0 — Personal Local release
- [ ] Validate Myanmar OCR reference images against rendered source pages.
- [ ] Run language-specific `mya` and `eng` benchmark on a provisioned machine; maintain CER ≤ 0.30 and WER ≤ 0.60 thresholds. Do not weaken thresholds to pass.
- [ ] Re-run representative copied-office pilot and resolve OCR timeouts/errors.
- [ ] Complete browser E2E beyond plan review: approve/apply → Final copy → backup → isolated restore → undo.
- [ ] Reconcile backup/restore timing claims to a reproducible artifact, dataset, commit and measurement method; record RTO/RPO.
- [ ] Run repository self-audit and full required test/security checks on exact release SHA; freeze only after all gates have evidence.

### P1 — Runtime / integration work
- [ ] Verify persisted consent and trusted subject/purpose/exact-resource-scope propagation at every external AI/embedding boundary; prove fail-closed behavior.
- [ ] Validate retry/circuit/failover, durable idempotency, DLQ, signed QStash, duplicate delivery, approval/resume/completion and scheduled-boundary behavior with runtime evidence.
- [ ] Verify RAG ingest → embed → search, persisted observability/alerts, and chat export/restore/retention/purge/transfer audit.
- [ ] Confirm cancellable search and isolated backend test database.

### P2/P3 — Deferred, not release blockers unless scope changes
- [ ] Google Drive multi-account OAuth, Shared Drives and virtual classification.
- [ ] Enterprise tenancy/RBAC, mobile, multi-region and distributed job takeover/leases.
- [ ] Future trains/phases only after scoped design, threat model, migration/rollback, capacity baseline and acceptance criteria are approved.

## Safety / change control
- Keep Personal Local independent of cloud services.
- Keep original source read-only and separate from writable workspace; use copied representative data.
- Use disposable cloud users and test objects. Never put tokens, service-role keys, provider secrets or OAuth refresh tokens in Git, logs, shell history or chat.
- No production deploy, route/DNS change, secret rotation, schema mutation, service creation or destructive data operation is authorized by this audit.
- Update this report and the canonical status/roadmap only when fresh evidence changes a gate; distinguish implementation, configuration, live test and release approval.
