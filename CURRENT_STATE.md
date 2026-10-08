# Doka Current State

## 1. Current Release
**Evidence-gated Personal Local release preparation with Cloud verification in parallel.** No gate is upgraded without direct evidence.

## 2. Current Phase
**Release close-out — Gates 3–12.**

## 3. Overall Status
- **Personal Local:** foundation implemented; real OCR benchmark data, real browser acceptance, copied-office pilot, and measured recovery drill remain required.
- **Personal Cloud:** foundation implemented; authenticated lifecycle, two-user isolation, B2/Drive recovery and full provider-boundary evidence remain pending.
- **Enterprise:** deferred.
- **Cloudflare Worker:** current live deployment is verified below.
- **Vercel:** project is inactive in the connected account, but the connector does not expose an explicit paused flag; retain VERIFY rather than infer owner-paused state.
- **Render:** no services were returned for the connected Render workspace; this is evidence of no accessible active Render runtime.

## 4. COMPLETED
- Phase A–E remediation work preserved as historical evidence.
- Documentation migration Phases 1–6.
- Personal Local foundation.
- Local Auth/Session/Restart/Replay implementation.
- Organization Apply/locking/limits/Undo implementation.
- Dependabot/secret-scan/lockfile/lint reconciliation.
- Personal Cloud foundation.
- Cloudinary provider-level recovery probe: upload, backup download, delete, and post-delete placeholder verification.

## 5. VERIFIED
- Gate 1: local auth/session/restart/replay code and automated safety verification; browser acceptance remains separate.
- Gate 2: organization apply/locking/limits/undo automated verification; browser acceptance remains separate.
- Gate 7: quality/dependency/security workflow evidence is green.
- Live Supabase migration head: 20261005113241_doka_audit_export_backup_actions — verified from the live migration list on 2026-10-08.
- Repository migration head: 20261007120000_doka_trigger_function_least_privilege. This is newer than the live head and must never be represented as live production state.
- Cloudflare Worker doka-ai-dms was most recently inspected at 100% traffic on Worker version 602 (2026-10-08). This is deployment evidence only. The connected Cloudflare account currently has **0 D1 databases**, so the new D1 job adapter is not live-backed yet.
- Render connected workspace: service listing returned no active services on 2026-10-08.
- Cloudinary provider-level recovery probe on 2026-10-08: 22-byte test object, SHA-256 42b68a292fea02d6220c0ee02a4489697758f19d4fb1420d9063697087583a1c; backup download returned exact payload; delete returned success; subsequent asset lookup returned a zero-byte placeholder, proving the original delivery object was removed. Tool-side duration was not exposed.

## 6. IN PROGRESS
- 2026-10-08 parallel checkpoint: live Supabase security advisor still has leaked-password protection WARN; live Cloudflare Worker deployment was inspected (version 602 at 100%). Neither observation closes application acceptance gates.
- Vercel connected project `enterprise-ai-dms` remains `live=false` with latest production deployment `CANCELED`; the latest GitHub commit status also reports a Vercel `failure` check attributed to a build-rate-limit target. This does not change the release-gate evidence decision.
- Train 1 checkpoint: concrete D1 job-idempotency/outbox adapters, AI retry/circuit/failover safety, and OCR-aware retrieval are implemented on `main`; runtime evidence remains pending because the connected Cloudflare account currently has no D1 database provisioned.
- Train 1/3 workflow hardening is targeted-runtime verified, and durable job-level idempotency state is now implemented/tested on `main`. Next contract backlog: retry taxonomy → retry exhaustion/DLQ → provider half-open/failover/consent/schema → multilingual retrieval → human approval.
- Train 1/3 hardening: workflow idempotency, D1 job idempotency, outbox retry/DLQ handling, AI circuit/failover/consent/schema boundaries, and OCR-aware retrieval safeguards are implemented; distributed worker takeover remains intentionally disabled.
- Live Supabase Security Advisor recheck on 2026-10-08 still reports `auth_leaked_password_protection` as WARN. The connected Supabase tool exposes no Auth security-setting mutation, so this remains a release/security-freeze blocker rather than an unverified claim.
- Gate 3: OCR benchmark evidence reconciliation.
- Gate 4: real browser Personal Local E2E.
- Gate 5: copied-office pilot and before/after source hashes.
- Gate 6: measured backup/restore RTO/RPO.
- Gate 9: authenticated Cloud lifecycle E2E.
- Gate 10: two-user isolation plus live RLS/Storage/API proof.
- Gate 11: B2 >50 MiB, Google Drive export/recovery, 50 MiB routing and complete provider recovery evidence.
- Final live-infrastructure evidence reconciliation.

## 7. PENDING
- Gate 3: current representative sample directory/manifest and Tesseract version are not available in the accessible test environment. A historical privacy-scrubbed report exists (5 mixed mya+eng samples; mean CER 0.1660492282; mean WER 0.3081550029), but it does not record Tesseract version and is not sufficient to close the current gate.
- Gate 4: the current Playwright suite is now aligned to the Personal Local acceptance flow (login → Safe Workspace → import → scan → understand/OCR → review plan → source hash comparison). The suite is implementation-ready, but no browser runtime/data acceptance run has been executed in the accessible test box.
- Gate 5: pilot harness and source-hash logic exist; only synthetic evidence is recorded. No copied representative office-data pilot has been run in this pass.
- Gate 6: synthetic backup/restore evidence exists; no timed real-machine drill was run, so RTO/RPO are unmeasured.
- Gate 9: live Worker unauthenticated probe returned HTTP 403; no disposable authenticated test-user session was available for the required lifecycle test.
- Gate 10: live Supabase is healthy with current migrations, but two real authenticated test users were not available. Existing synthetic RLS probes are not accepted as two-user release evidence.
- Gate 11: Cloudinary provider-level recovery verified; B2 and Google Drive live credentials/connectors are not available. Therefore the complete storage/recovery gate remains PENDING.
- Vercel explicit paused-state evidence: the connected Vercel project reports live=false and latest production deployment CANCELED, but the API response exposes no explicit paused-state field. Keep VERIFY for the exact owner-paused claim.

## 8. BLOCKED
- Gate 8: Personal Local final freeze, blocked until Gates 1–7 are fully evidenced.
- Gate 12: deployment/final go-live, blocked until Gates 9–11 are fully evidenced.

## 9. DEFERRED
- Enterprise edition and enterprise RBAC.
- Phase 7/8 activation evidence and production runtime validation.
- Phase 9–18 future expansion tracks.
- Cloud-first approaches preserved in archive as historical material.

## 10. REMAINING RELEASE GATES
| Gate | Status |
|---|---|
| 1 Local auth/session/restart/replay | Implemented / automated verified; browser pending |
| 2 Organization Apply/locking/limits/Undo | Implemented / automated verified; browser pending |
| 3 OCR limits + Myanmar/English benchmark | PENDING |
| 4 Personal Local browser E2E | PENDING |
| 5 Copied-office pilot + source hashes | PENDING |
| 6 Backup/restore + measured RTO/RPO | PENDING |
| 7 Dependabot/secret/lockfile/lint | VERIFIED |
| 8 Personal Local final freeze | BLOCKED |
| 9 Cloud authenticated E2E | PENDING |
| 10 Two-user isolation + RLS | PENDING |
| 11 Storage provider/recovery + 50 MiB | PENDING |
| 12 Deployment/runtime + final sign-off | BLOCKED |

## 11. LAST VERIFIED
- Disposable runtime checkpoint 2026-10-08: Python 3.13, Node 22, npm 10, Playwright 1.64 available; Tesseract absent; required backend Python modules absent. Acceptance preflight returned not-ready without recording secrets.
- Workflow targeted runtime checkpoint 2026-10-08: 6/6 workflow contract tests passed in the disposable runtime after idempotency/locking hardening. Full backend suite was not rerun.
- Durable job idempotency contract: claim/state/attempt persistence, retry exhaustion, DLQ transition and concurrent duplicate claims are now covered by focused contract tests; no queue takeover is enabled.
- Maintained backend regression suite: 386 passed in the latest recorded full run; this pass could not rerun pytest because the accessible execution box has no pytest/pip installation.
- Frontend lint/build/smoke: latest recorded run passed.
- Quality + CodeQL evidence: latest recorded workflow run passed.
- Live Supabase head: 20261005113241_doka_audit_export_backup_actions, freshly verified on 2026-10-08.
- Cloudflare Worker: latest inspected 100% traffic version 602 on 2026-10-08; no rollback or traffic change was performed.
- Render: connected workspace returned no services.
- Cloudinary: provider-level recovery probe passed on 2026-10-08 as recorded above.
- Vercel: project inactive/latest production deployment canceled; explicit paused flag unavailable.

## 12. NEXT ACTION
**Owner-provided runtime evidence is now the critical path.** The repository is prepared through Gates 3–11: Personal Local OCR/pilot/browser/recovery runners are ready, and `scripts/cloud_acceptance.py` is ready for Gate 9/10 with two pre-created user access tokens plus an exact 50 MiB fixture. Gate 11 still requires live B2 and Google Drive credentials/connectors and a real Cloudinary application-path run. Then rerun only the blocked gates, record measured evidence, and close Gate 8 before Gate 12.

- Train 1 safety contracts are now wired into concrete paths where the repository has them: D1 jobs/outbox, unified AI provider routing, and vector retrieval. Remaining evidence is runtime/provider acceptance; no concrete queue consumer exists in the current Worker, and D1 is not provisioned in the connected account.


## 13. TRAIN 1 CONCRETE INTEGRATION CHECKPOINT — 2026-10-08
- Durable D1 job adapter: implemented in cloudflare_worker/jobs.py against the existing jobs table schema (unique idempotency_key, bounded attempts, terminal success/dead states). No lease takeover is enabled.
- Outbox: actual delivery failures now use a conservative retry taxonomy; permanent failures dead-letter immediately and transient failures use bounded backoff.
- AI: unified_ai_service now uses the Train 1 circuit breaker and retry taxonomy; provider failover is opt-in via AI_PROVIDER_FAILOVER_APPROVED and structured/non-retryable failures fail closed.
- Retrieval: vector_search now canonicalizes OCR text to Unicode NFC, validates mya/eng identity + SHA-256, scopes ranking by language, and uses deterministic local ranking for Myanmar OCR instead of the English-centric embedding model.
- Runtime constraint: Cloudflare account inspection returned zero D1 databases, so D1 runtime acceptance cannot honestly be marked PASS. Provider runtime evidence and Myanmar/English benchmark remain pending.


## 14. TRAIN 1 CI RECONCILIATION — 2026-10-08
- Concrete Train 1 implementation is CI-verified on main: Doka Quality Checks passed and CodeQL passed on the final implementation commit 06f6874aa999fec441bbb285327a17af795625c2.
- The Quality run covered backend regression (including Train 1 safety/AI/retrieval tests), Cloudflare job/outbox/storage contracts, dependency audits, static/SBOM checks, frontend lint/build/smoke, and symlink security.
- This closes the implementation/CI portion of Train 1. It does **not** close live evidence gates that require real OCR tooling, browser data, authenticated cloud users, provider recovery, or provisioned D1 infrastructure.


## 15. TRAIN 1 RUNTIME EVIDENCE STATUS — 2026-10-08
- Concrete integration remains CI-verified: latest Doka Quality Checks **SUCCESS** and CodeQL **SUCCESS** on commit `ce328544a1b88b32fb53bd01227789bcbf3446a0`.
- Live Cloudflare Worker is version 631 at 100% traffic.
- Live D1 cannot yet be proven because the connected Cloudflare account has zero D1 databases. A disposable live D1 acceptance runner is prepared but intentionally not executed without a real database.
- Supabase Auth leaked-password protection remains a security-freeze blocker.
