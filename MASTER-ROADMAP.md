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
- **Phase 5 preparation:** Dependabot configuration and lockfiles are present; frontend smoke checks now include auth namespace isolation. Full dependency/security reconciliation still requires the current GitHub alert/run evidence before release sign-off.

## The 12 remaining release gates

| # | Gate | Status |
|---|---|---|
| 1 | Local auth/session/restart/replay + auth-state permissions | Pending verification |
| 2 | Organization Apply / locking / limits / Undo | Pending verification |
| 3 | OCR resource limits + Myanmar/English benchmark | Pending verification |
| 4 | Real browser Personal Local E2E | Pending verification |
| 5 | Copied-office pilot + source before/after hashes | Pending verification |
| 6 | Backup/restore proof + measurable local RTO/RPO | Pending verification |
| 7 | Dependabot/secret-scan/lockfile/lint reconciliation | Pending verification |
| 8 | Personal Local final freeze + release evidence/runbook | Blocked by 1–7 |
| 9 | Cloud authenticated lifecycle E2E | Pending verification |
| 10 | Two-user isolation + Supabase RLS/Storage/RPC proof | Pending verification |
| 11 | B2/Cloudinary/Google Drive + 50 MiB + recovery proof | Pending verification |
| 12 | Deployment/runtime evidence + final go-live sign-off | Blocked by 9–11 |

## Next phase bundles already prepared

1. **Phase 5A — Quality/Supply-chain closeout:** run the existing Doka Quality Checks, Dependency Review, CodeQL, frontend audit/lint/build/smoke, backend regression/coverage, secret scan and SBOM; reconcile only confirmed findings and keep lockfiles authoritative.
2. **Phase 5B — Local release evidence:** real browser acceptance → copied-office pilot → source hash comparison → OCR Myanmar/English benchmark → backup checksum → isolated restore → measured RTO/RPO → final local runbook/evidence.
3. **Phase 6A — Cloud acceptance:** authenticated lifecycle → two-user isolation → RLS/Storage/RPC proof → 50 MiB/recovery/provider boundary checks → Supabase leaked-password protection verification.
4. **Phase 6B — Deployment gate:** verify Cloudflare runtime and production frontend only when authorized; Vercel remains paused unless explicitly reopened; then assemble final release evidence and sign-off.
5. **Advanced Phase 3/4 only after release:** worker scaling, distributed locks/retries, cloud AI budgets/circuit breakers, RAG/embeddings, compliance, multi-region and mobile work remain deferred until measured demand and approved scope.

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
