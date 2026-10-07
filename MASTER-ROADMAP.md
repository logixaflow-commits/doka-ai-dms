# Doka Master Roadmap

Last reconciled: 2026-10-07

> **Front door / live status dashboard.** This is the document to open first. Detailed execution rules remain in `docs/DOKA_UNIFIED_REMEDIATION_ROADMAP.md`. Historical plans are not execution authorities.

## Final goal

Doka is complete only when the required **real evidence** passes—not merely because code exists or CI is green.

**Personal Local first:** login → import copied source → scan/OCR → review → human approval → copy to Final → backup → isolated restore → undo, with source hashes unchanged.

**Cloud second:** authenticated lifecycle → two-user isolation → storage/recovery → security settings → deployment/runtime evidence.

## Current truth

- **Code foundation:** substantially implemented.
- **Personal Local:** **not release-signed-off**; real browser + copied-office pilot + OCR benchmark + backup/restore/RTO/RPO evidence are still required.
- **Cloud:** foundation is implemented, but authenticated E2E, two-user isolation and provider recovery evidence are still required.
- **Vercel:** project exists but remains **owner-paused**; do not reactivate or deploy unless explicitly authorized.
- **Cloudflare:** active Worker `doka-ai-dms` exists and was modified 2026-10-07.
- **Supabase:** project `Enterprise AI DMS` is healthy; the remaining Security Advisor warning is leaked-password protection.
- **Render:** inspected current workspace; no Render services are currently exposed, so there is no active Render runtime to audit.
- **AI:** capability-based routing is wired for implemented providers; Mistral/Cerebras/NVIDIA require complete model+endpoint configuration, while Cohere/Voyage/Cloudflare remain roadmap-only until dedicated adapters exist. Unimplemented providers stay fail-closed even when a key is present. OCR now uses runtime-configurable Poppler settings. Live Cloudflare Worker has no AI-provider secrets configured. Local real `.env` values are not committed and therefore cannot be verified from GitHub.
- **Phase 1→4 coding-side reconciliation (current batch):** backend session-operation locking and source/Final/backup containment remain enforced; backup restore is isolated and archive-hash verified. AI document output is now schema-validated before entering Doka, embedding routing honors configured provider order and has a deterministic local similarity fallback, and unsupported providers remain fail-closed. Personal Local and Cloud browser sessions now use separate storage namespaces, and refresh-token rotation is serialized to avoid concurrent refresh invalidation. Regression coverage was added for AI boundaries, backup restore/ZIP safety, and frontend session isolation.
- **Phase 5 coding/CI preparation:** Dependabot configuration, npm/uv lockfiles, backend/frontend/security workflow coverage, SBOM generation and dependency-review gates are present. A workflow-configuration sanity job and cloud-storage 50 MiB boundary regression were added. Current GitHub workflow evidence is still required before marking Phase 5 verified.

## The 12 remaining release gates

| # | Gate | Status |
|---|---|---|
| 1 | Local auth/session/restart/replay + auth-state permissions | Pending verification |
| 2 | Organization Apply / locking / limits / Undo | Pending verification |
| 3 | OCR resource limits + Myanmar/English benchmark | Pending verification |
| 4 | Real browser Personal Local E2E | Pending verification |
| 5 | Copied-office pilot + source before/after hashes | Pending verification |
| 6 | Backup/restore proof + measurable local RTO/RPO | Pending verification |
| 7 | Dependabot/secret-scan/lockfile/lint reconciliation | Pending verification (CI evidence required; frontend lint is now enforced) |
| 8 | Personal Local final freeze + release evidence/runbook | Blocked by 1–7 |
| 9 | Cloud authenticated lifecycle E2E | Pending verification |
| 10 | Two-user isolation + Supabase RLS/Storage/RPC proof | Pending verification |
| 11 | B2/Cloudinary/Google Drive + 50 MiB + recovery proof | Pending verification |
| 12 | Deployment/runtime evidence + final go-live sign-off | Blocked by 9–11 |

## Latest coding-side verification — 2026-10-07

- Personal Local maintained regression suite: **46 passed** on the current main HEAD; this covers AI boundaries, local auth/session, source containment, Unicode passwords, OCR limits, backup restore/route boundaries, and symlink safety.
- Cloud storage contract unit suite: **13 passed** on the current main HEAD.
- Frontend: **lint, production build, and smoke suite passed** on the current main HEAD.
- Quality workflow YAML (doka-quality.yml, CodeQL, Dependency Review) parsed successfully in the same isolated runner; all six backend dependency profile files are present.
- A real backup restore bug was fixed: invalid ZIP archives are now fully validated before Recovery/ is created, preserving failure atomicity.
- Live Supabase project audit: all three exposed Doka tables have RLS enabled with owner-bound policies; current Doka public RPCs do not grant EXECUTE to anon, and the inspected document/version RPCs are SECURITY INVOKER.
- Supabase Security Advisor still reports **Leaked Password Protection Disabled**; this requires the Supabase Auth project setting and remains an explicit Phase 6 acceptance gate.
- Release workflow was narrowed to maintained Personal Local tests instead of collecting stale legacy enterprise tests that reference removed ORM/routes. Those legacy tests remain evidence debt, not release-gate blockers.
- GitHub Actions verification: Doka Quality Checks SUCCESS on commit 4bc041935b596433a580257f35125483d87db044; maintained backend regression, cloud storage contracts, symlink security, frontend lint/build/smoke, workflow sanity, root dependency audit, secret scan, Semgrep baseline and SBOM all succeeded. CodeQL SUCCESS on the same commit.

## Phase 8 implementation status

- AI provider circuit breaker is implemented for configured providers: consecutive-failure threshold, cooldown window, half-open retry, success reset, and fallback-aware skipping.
- Provider resilience configuration is documented in `.env.example` and `docs/AI_PROVIDER_MATRIX.md`.
- Dedicated Cohere/Voyage/Cloudflare adapters remain gated until adapter contracts, privacy/cost benchmarks and credentials are explicitly approved.

## Next phase bundles already prepared

1. **Phase 5A — Quality/Supply-chain closeout:** run the existing Doka Quality Checks, Dependency Review, CodeQL, frontend audit/lint/build/smoke, backend regression/coverage, secret scan and SBOM; reconcile only confirmed findings and keep lockfiles authoritative.
2. **Phase 5B — Local release evidence:** real browser acceptance → copied-office pilot → source hash comparison → OCR Myanmar/English benchmark → backup checksum → isolated restore → measured RTO/RPO → final local runbook/evidence.
3. **Phase 6A — Cloud acceptance:** authenticated lifecycle → two-user isolation → RLS/Storage/RPC proof → 50 MiB/recovery/provider boundary checks → Supabase leaked-password protection verification.
4. **Phase 6B — Deployment gate:** verify Cloudflare runtime and production frontend only when authorized; Vercel remains paused unless explicitly reopened; then assemble final release evidence and sign-off.
5. **Phase 7 — Post-release hardening bundle:** production observability, incident/error workflow, performance baseline, backup monitoring, dependency update automation, security regression scheduling, rollback rehearsal, and operational runbook refinement.
6. **Phase 8 — Advanced Doka intelligence/scale bundle:** provider circuit breakers and budgets, dedicated Cohere/Voyage/Cloudflare adapters, stronger RAG/embedding evaluation, distributed workflow scaling, advanced search, compliance/audit expansion, team features, mobile alignment, and multi-region readiness.
7. **Phase 9 — Controlled Product Expansion:** enterprise organizations/membership/RBAC, sharing, integration scopes and regulated-workload policy tracks; requires two-tenant isolation, role-matrix, audit and migration/rollback evidence.
8. **Phase 10 — Scale & Reliability:** distributed jobs/leases, queue-backed OCR/AI workloads, idempotency, bounded retries/dead-letter handling, load/failure injection and DR orchestration; distributed coordination must never silently degrade to unsafe single-worker behavior.
9. **Phase 11 — Advanced Intelligence:** multilingual RAG, embedding/reranking benchmarks, provider cost/quality routing, regression corpus, human feedback and semantic search; Reader → Planner → Human Approval → Executor remains mandatory.
10. **Phase 12 — Enterprise / Mobile / Multi-region:** team governance, advanced compliance/audit, production mobile, resumable upload, data residency and multi-region failover; each has independent device/region/recovery acceptance.
11. **Cross-phase rule:** Phase 9–12 features remain separate activation tracks and must not become hidden dependencies of Personal Local or Personal Cloud core release.

**Credential rule:** no live provider/storage keys are needed for the current coding-side work. If a later acceptance gate truly requires a live credential, request the exact key(s) and purpose immediately before that gate rather than adding secrets early.

### What is already finished

- Phase A–E planning was consolidated into the unified remediation roadmap.
- Current UI, architecture and tools boundaries have dedicated source-of-truth docs.
- Sensitive Cloud API routes were tightened to admin-only where cross-user data exposure was possible.
- Supabase version RPC execution was hardened and the corresponding security finding was cleared.
- Tracked Wrangler local account cache was removed and `.wrangler/` is ignored.
- Vercel production pause is explicitly documented and protected from accidental reactivation.

### What is **not** allowed to be called finished

- Unit/CI tests alone do not close a real-machine gate.
- A configured provider key does not prove that the provider works.
- A deployment existing does not prove authenticated production readiness.
- An AI adapter existing does not prove safe agent behavior.
- A green Supabase advisor does not replace two-user isolation testing.

## AI / agent boundary

Use a strict three-stage contract:

**Reader → Planner → Executor**

1. **Reader:** read/extract/OCR/classify evidence; read-only; no filesystem mutation.
2. **Planner:** produce structured proposals with provider/model/confidence/reason; no filesystem mutation.
3. **Executor:** accepts only a human-approved plan; performs bounded copy/rename/metadata operations; logs every action and supports undo.

Duplicate/version analysis should remain deterministic/local first. AI is an optional advisor, not the source of truth.

Recommended provider roles and task-specific fallback chains are documented in `docs/AI_PROVIDER_MATRIX.md`. Environment ownership and live-service findings are documented in `docs/ENVIRONMENT_MATRIX.md`.

## Documentation update rule / reminder

**After every completed phase, and at minimum after every 3 release gates:**

- update this file's date/status table;
- mark each gate only as `Implemented`, `Verified`, `Pending verification`, `Deferred`, or `Blocked`;
- record the exact evidence source (test run, browser result, live config, pilot result, or recovery drill);
- update `README.md` only when the public/current product status changes;
- update the relevant focused doc only when its boundary changes;
- do **not** create a new status MD for every phase;
- do **not** leave completed work in a separate pile of “finished” files;
- historical plans stay under `docs/legacy/` and are never execution authorities.

**Reminder:** when gates **1–3**, **4–6**, **7–9**, or **10–12** are closed, stop and reconcile this roadmap before starting the next group.

## Current execution order

1. Close gates 1–3.
2. Run gate 4 browser acceptance.
3. Run gates 5–6 pilot/recovery.
4. Close gates 7–8 and freeze Personal Local.
5. Run gates 9–11 for Cloud.
6. Close gate 12 and issue final sign-off.
7. Only then evaluate deferred enterprise/mobile/advanced AI/scale work.

Detailed issue IDs, architecture backlog and deferred work remain in `docs/DOKA_UNIFIED_REMEDIATION_ROADMAP.md`.

## Documentation cleanup policy

Keep only one active document per concern:

- roadmap/status → this file
- detailed execution/issues → `docs/DOKA_UNIFIED_REMEDIATION_ROADMAP.md`
- UI → `docs/UI.md`
- architecture → `docs/ARCHITECTURE.md`
- tools/services → `docs/TOOLS.md`
- local operations → `docs/PERSONAL_LOCAL_RUNBOOK.md`
- security → `SECURITY.md`
- cloud API/security → existing cloud contract/security docs
- environment inventory → `docs/ENVIRONMENT_MATRIX.md`
- AI/provider/agent policy → `docs/AI_PROVIDER_MATRIX.md`

If two documents become duplicates, merge their unique information into the active authority, then delete or move the obsolete copy to `docs/legacy/`. Never delete a document before checking its unique content and inbound references.
