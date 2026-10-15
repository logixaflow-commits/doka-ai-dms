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
