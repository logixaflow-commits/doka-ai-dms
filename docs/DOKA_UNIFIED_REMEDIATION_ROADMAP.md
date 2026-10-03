# Doka Unified Remediation & Delivery Roadmap

Last reconciled: 2026-10-03  
Inputs: the existing Phase A–E delivery gate, Personal Local Master Plan, Master Product Plan, Phase A audit, and the newly added Executive Summary of Remediation Plan.  
Product priority: **Personal Local Edition first**. Cloud/enterprise/mobile work remains gated and must not destabilize the local product.

## 1. How to use this roadmap

This is the single execution map for remaining work. It consolidates the previous A–E work with the new remediation issue register. The original remediation issue IDs are retained so nothing is silently dropped.

Status meanings:
- **Implemented (code)** — implementation is present; this does not prove real-world acceptance.
- **Verified** — supported by a recorded test, audit, or live configuration check.
- **Pending verification** — code or configuration exists, but its required end-to-end or real-machine evidence is missing.
- **Deferred** — belongs to a later edition or depends on a prior release gate.
- **Needs audit** — must be inspected against current code/data before changing it.

No item is marked complete merely because a sample snippet or proposed architecture exists.

## 2. Non-negotiable boundaries

1. Original source data is read-only: `ORIGINAL_READ_ONLY=true`, `ALLOW_SOURCE_WRITE=false`.
2. All processing and organization happen on a verified working copy; no source-root writes, destructive moves, or overwrite of different content.
3. Human approval remains mandatory for organization proposals. Review/duplicate/version items are never auto-approved.
4. Backups restore only into an isolated recovery location; restore must not silently replace the active workspace.
5. Personal Local must work without Supabase, Redis, MinIO, Vercel, Render, Cloudflare, or AI credentials.
6. AI is disabled by default, external processing requires explicit consent, and AI cannot perform destructive filesystem actions.
7. Do not enable paid/card-required infrastructure without explicit approval.
8. Vercel production stays paused/off. No production deploy, alias change, or reactivation is part of this roadmap unless explicitly authorized.
9. Keep GitHub Actions lean. Do not dispatch/rerun workflows just to obtain reassurance; use focused local checks and existing evidence first.
10. Keep deferred enterprise/mobile modules isolated from the Personal Local runtime.

## 3. Re-based phases

### Phase 0 — Reconciliation, repository hygiene and dependency triage
**Purpose:** establish one accurate backlog and remove known build/security debt without broad risky refactors.

Work:
- Reconcile this roadmap with `DOKA_PHASE_A_TO_E_STATUS.md`, `PHASE_A_AUDIT.md`, and current source before each implementation batch.
- Review the reported npm advisories individually; choose compatible patched versions, update lockfiles intentionally, and avoid blind major upgrades.
- Reconcile frontend manifest and lockfile metadata before dependency changes; the 2026-10-03 check found matching root dependency declarations, but this is not a vulnerability audit.
- Keep the local test guide aligned with the current Python 3.12 / Node.js 24.x toolchain and the exact backend, frontend lint/build/smoke commands; distinguish code-level tests from real-office copied-data pilot evidence.
- Retrieve and classify the full Dependabot alert inventory when repository permissions expose it; the earlier audit could only confirm the user's approximate count, not each alert.
- Reduce the recorded ESLint baseline in small batches (unused imports/variables first, then unsafe any, effect dependencies/state-in-effect, React Refresh and immutability findings); only make lint blocking after the baseline is genuinely clean.
- Review root-level launchers/configs before moving anything; preserve consumers and keep active runtime under `web-platform/`.
- Keep root Windows/POSIX launchers aligned with the frontend Node.js `24.x` engine and stop early with an actionable prerequisite error.
- Keep automatic CI consolidated and report-only where a known baseline is intentionally being burned down.

Exit criteria:
- Every alert/finding has a disposition: fixed, accepted with reason, or blocked by compatibility.
- Lockfiles and package manifests agree.
- No root cleanup breaks local launch/build paths.
- No unverified "all clear" claims.

### Phase 1 — Personal Local security and workflow release gate
**Purpose:** finish proving the product that is actually being built now.

Work:
- Re-audit local authentication, token invalidation, logout, environment guards, session switching, and workspace API boundaries.
- Enforce `ORIGINAL_READ_ONLY=true` and `ALLOW_SOURCE_WRITE=false` at source-validation time; require `FINAL_ROOT` to be a dedicated path inside `WORKING_ROOT` and isolated from `SOURCE_ROOT`.
- Keep Supabase-backed Cloud API routers out of the Personal Local entry point; use the dedicated cloud entry point for cloud document/storage APIs.
- Keep `BACKUP_ROOT` disjoint from source/workspace paths, reject symlink roots, and reject cross-platform unsafe/case-colliding archive paths during restore.
- Restrict the persistent local authentication SQLite state file to owner-only permissions on POSIX systems.
- Close remaining test gaps around production/staging denial for local auth endpoints and process-restart semantics; persist local token revocation, session-family logout and refresh replay state in SQLite without requiring cloud DB/Redis.
- Verify Organization Apply limits, duplicate-path rejection, per-session locking, incremental hash checks, and Undo behavior against implementation and tests.
- Serialize Safe Workspace status/list/search/inventory/understanding reads with same-session mutations so Windows polling cannot race atomic JSON replacement; retain the single-process limitation.
- Verify OCR pixel/page/resource limits and representative Myanmar/English extraction; ensure image/PDF handling fails safely on malformed/oversized input.
- Verify the pilot harness against the actual output schema and its test fixtures. Confirm it checks copied source hashes, import completeness, scan readability, actual OCR results, backup verification, isolated restore manifest equality, and cleanup.
- Finish frontend workflow-state boundary review: no stale OCR results, proposals, selected approvals, or session data leak between import sessions.
- Document the production Personal Local build contract: `VITE_DOKA_EDITION=personal-local`; backend `ENVIRONMENT=local` or `development`; do not configure Supabase credentials for local auth mode.
- Run focused local tests and frontend build/smoke tests when the execution environment is available; record exact commands/results. Do not claim tests pass without execution.

Exit criteria:
- Security regression tests and frontend smoke/build checks pass.
- A browser walkthrough on a running local instance succeeds from login through import, scan/OCR, review, approve, copy-to-Final, backup, restore-to-Recovery and undo.
- No source mutation; before/after hash manifests match.
- No unresolved critical/high safety issue.

### Phase 2 — Real-office copied-data pilot and Personal Local stabilization
**Purpose:** turn implemented features into proven office-ready behavior.

Work:
- Run `python scripts/doka_pilot_check.py --source <COPY_OF_REAL_OFFICE_DATA> --require-ocr` on a separate representative copy, never on the original drive.
- Record import verified/failed/unverified counts, scan completeness, Myanmar/English OCR examples, duplicate/version false positives, review outcomes, backup checksum, restored manifest, and source before/after hashes.
- Tune OCR, language detection, extraction, duplicate/version grouping and organization rules only from reproducible pilot findings.
- Add sanitized representative regression fixtures for every corrected defect.
- Verify restore drills and document practical RTO/RPO for the local product; publish recovery and incident runbooks.
- Verify large-file behavior and resumability against actual local limits before selecting multipart/tus/cloud object storage.
- Confirm private VPN/tunnel access only if remote-office access is required; no public port-forwarding.

Exit criteria:
- Pilot gate passes on copied office data.
- No unexplained source or working-copy mutations.
- OCR/search/duplicate decisions are reviewed and measurable.
- Backup restore is independently verified.
- Local browser workflow is repeatable without manual repair.

### Phase 3 — Cloud edition security and operational completion (separate from Personal Local)
**Purpose:** finish the already-started cloud foundation only after local pilot evidence; keep it a distinct runtime.

Work:
- Complete real authenticated cloud browser E2E: sign-in, upload, search/list, preview/download, metadata update, Trash/Restore/permanent delete, versions and audit.
- Test two-user isolation for every API, database and Storage operation; verify owner-scoped RLS and effective grants after migrations.
- Reconcile dependency and security findings for cloud worker/frontend; add SAST/DAST/SBOM only with an affordable, non-duplicative CI design.
- Add PII redaction and telemetry scrubbing verification; do not send document contents, OCR text, secrets or sensitive paths to observability.
- Add cloud API contract checks and OpenAPI artifact export where useful.
- Implement AI consent enforcement, prompt-injection defenses, per-workspace cost limits, rate limiting, response caching and provider audit metadata before enabling external AI.
- Decide remote OCR/worker hosting only from Phase 2 workload measurements and free-tier/cost constraints.
- Vault/KMS migration is a cloud/production concern; design a staged migration and rollback, but do not introduce Vault as a dependency for Personal Local.
- Review Supabase RLS/Storage policies with least privilege; enterprise ABAC/OPA is not required for the single-user local runtime.

Exit criteria:
- Authenticated cloud lifecycle E2E and cross-user isolation pass.
- No service-role secrets in browser or public artifacts.
- Storage overwrite protections and audit records verified.
- External AI is blocked when consent is false and budget controls are enforced.
- Cloud services remain optional and isolated from local operation.

### Phase 4 — Scale, resilience, compliance and advanced product maturity
**Purpose:** implement only capabilities justified by an active cloud/enterprise/mobile product and operational requirements.

Work:
- Database query optimization, indexes, transaction/idempotency refactors, optimistic locking, and file-lock lease/heartbeat work.
- Worker separation, retry/backoff/circuit breakers, dead-letter handling, global distributed rate limiting, cache invalidation, CDN and WAF/API gateway as appropriate.
- Immutable encrypted geo-replicated backups, multi-region/replica strategy and tested failover with agreed RTO/RPO.
- Formal compliance work (data classification, export/delete/SAR, retention, KMS encryption, audit retention, policy/DPA/SOC2 evidence) only after scope and legal requirements are established; do not claim GDPR/HIPAA/SOC2 certification from code changes.
- ABAC/ReBAC (OPA/Casbin), Supabase RLS review, and organization-level permission model for multi-user tenants.
- Frontend i18n, offline support, accessibility, E2E/unit/coverage gates, load/chaos testing, strict TypeScript, circular-dependency and dead-code cleanup.
- Mobile upload resume, image caching, FlatList optimization, offline sync/conflict resolution and app-store readiness only when mobile is actively in scope.
- Developer experience: DevContainer, seeded docker-compose, ADRs, CODEOWNERS, release checklist and optional monorepo tooling.

Exit criteria:
- Every introduced component has an owner, runbook, rollback path, cost profile and automated/manual verification.
- SLO/RTO/RPO targets are measured in drills, not merely documented.
- Enterprise/mobile work does not leak into Personal Local startup or dependencies.

## 4. Remediation issue register — all source IDs retained

The phase assignment below is the new execution grouping. The original plan's estimates/owners remain planning hints, not commitments. "Later" means Phase 4 unless the issue is pulled forward by a demonstrated blocker.

### Security & compliance
| Issue | New phase | Action / disposition |
|---|---|---|
| SEC-001 | 0 | Secret scanning baseline + PR scan; avoid duplicate CI workflows. |
| SEC-002 | 1 | Verify safe CORS validation against actual credential configuration and tests. |
| SEC-003 | 1 | Enforce startup config validation and unsafe-production-config rejection. |
| SEC-004 | 1 | Minimize/sanitize config endpoint; remove filesystem paths and secrets. |
| SEC-005 | 3 | Runtime external-AI consent enforcement; local AI remains disabled by default. |
| SEC-006 | 3 | CodeQL/Semgrep and staging DAST after staging exists; avoid public production scans while paused. |
| SEC-007 | 3 | Generate Syft SBOM as build artifact without adding another redundant workflow. |
| SEC-008 | 3 | Vault/KMS for cloud/production only; rotate keys with rollback plan. |
| SEC-009 | 4 | Data classification, export/delete, retention, encryption and compliance evidence; XL/legal scope. |
| SEC-010 | 4 | ABAC/ReBAC via OPA/Casbin for multi-user authorization; benchmark before rollout. |
| SEC-011 | 3 | Review Supabase RLS/grants/Storage policies and preserve least privilege. |
| SEC-012 | 3 | PII redaction and Sentry/log scrubbing tests. |
| SEC-013 | 1 | Service worker must not cache authenticated documents, API responses or signed content. |
| SEC-014 | 1 | Audit backup DB URL parsing and secure subprocess invocation. |
| SEC-015 | 0/3 | Dependency scanning: reconcile npm/Python/Dependabot findings; use one efficient source per ecosystem. |

### Backend, database and processing
| Issue | New phase | Action / disposition |
|---|---|---|
| BE-001 | 2 | Measure and complete non-blocking/streaming I/O where pilot workloads require it. |
| BE-002 | 3 | Fix cloud/backend N+1 query patterns using measured query plans. |
| BE-003 | 3 | Correct permission filtering/pagination semantics; verify owner isolation. |
| BE-004 | 3 | Add indexes based on actual query patterns and EXPLAIN evidence. |
| BE-005 | 3 | Transactional bulk operations with rollback tests. |
| BE-006 | 3 | Idempotent document processing and transaction boundary refactor. |
| BE-007 | 3 | Worker retries, backoff, timeouts, acknowledgements and DLQ. |
| BE-008 | 2/3 | OCR/AI per-stage retry and circuit-breaker behavior; local OCR first, cloud workers later. |
| BE-009 | 1 | Verify local per-session locking for mutable-state reads/writes and atomic writes; DB-backed version metadata is later. |
| BE-010 | 0 | Confirm duplicate return cleanup in lock-status path; add focused test if still present. |
| BE-011 | 1/3 | Replace silent empty returns with explicit diagnostics in active local/cloud paths. |
| BE-012 | 2/3 | Large-file resumable/multipart uploads after local pilot measurements; no premature paid storage. |
| BE-013 | 3 | Lock TTL/lease/heartbeat for shared worker or multi-instance operation. |
| BE-014 | 3 | Optimistic locking/version column for concurrent cloud updates. |
| BE-015 | 3 | Prevent orphaned shares and define user lifecycle for multi-user cloud. |
| BE-016 | 1 | Verify OCR heavy work is bounded/off request path; Celery only for cloud/worker runtime, not required locally. |

### Architecture & scalability
| Issue | New phase | Action / disposition |
|---|---|---|
| ARCH-001 | 3 | Separate web/API and worker deployment units only for cloud scale; keep local simple. |
| ARCH-002 | 3 | Redis/global distributed limiter for multi-instance cloud; retain local-safe limits. |
| ARCH-003 | 3 | CDN for public static assets only; private document content remains authenticated. |
| ARCH-004 | 3 | WAF/API gateway for a live public cloud API; no production activation now. |
| ARCH-005 | 3 | Redis cache-aside, TTL and invalidation after measuring cacheable workloads. |
| ARCH-006 | 3/4 | HA DB/read replicas when cloud traffic and RPO/RTO justify them. |
| ARCH-007 | 4 | Multi-region failover and cross-region replication with tested DNS/rollback. |

### AI/ML
| Issue | New phase | Action / disposition |
|---|---|---|
| AI-001 | 3 | Prompt-injection defenses and untrusted-document boundaries; test adversarial inputs. |
| AI-002 | 3/4 | RAG chunking, vector DB choice, embedding versioning and monitoring after demand is proven. |
| AI-003 | 3 | Per-workspace budgets, provider caps, rate limits, cache and kill switch before broad AI enablement. |
| AI-004 | 4 | Drift evaluation/alerts and retraining workflow only when model predictions and labels exist. |
| AI-005 | 3 | Redis response cache with privacy-aware keys/TTL/invalidation where cloud AI is enabled. |

### Disaster recovery & operations
| Issue | New phase | Action / disposition |
|---|---|---|
| DR-001 | 2 | Define local RTO/RPO and record measurable recovery objectives. |
| DR-002 | 2 | Repeatable isolated restore drills and recorded evidence. |
| DR-003 | 2/3 | Local recovery runbook first; DB/worker/AI outage runbooks for cloud later. |
| DR-004 | 4 | Immutable encrypted geo-replicated object backups for cloud/enterprise; local backup remains usable without this. |

### Frontend
| Issue | New phase | Action / disposition |
|---|---|---|
| FE-001 | 0/1 | Verify SSR-safe theme behavior only where SSR is used; current Vite runtime is client-rendered. |
| FE-002 | 0 | Confirm setter/API naming consistency during touched-code review. |
| FE-003 | 1/3 | Route-level code splitting where bundle measurements show benefit. |
| FE-004 | 1 | Memoize context values where profiling/lint findings justify it. |
| FE-005 | 1 | Verify token refresh, retry/backoff and AbortController in cloud API client. |
| FE-006 | 1 | Ensure effect cleanup and stable dependencies in active frontend paths. |
| FE-007 | 4 | Myanmar/English and additional locale pipeline when localization scope is agreed. |
| FE-008 | 1/3 | Graceful degradation for local runtime first, cloud services second. |
| FE-009 | 4 | Offline-first IndexedDB/background sync only with conflict and privacy design. |
| FE-010 | 1 | Service-worker update lifecycle and safe cache rules. |
| FE-011 | 4 | Centralize design tokens when design-system refactor is scheduled. |
| FE-012 | 1 | Accessibility audit and high-impact fixes for active screens. |
| FE-013 | 1/3 | Unit tests for critical local workflow components, then broader coverage. |
| FE-014 | 1/3 | Browser E2E for login/import/review/approve; cloud flows after cloud gate. |
| FE-015 | 4 | TypeScript strictness migration in focused batches after baseline inventory. |

### Mobile
| Issue | New phase | Action / disposition |
|---|---|---|
| MOB-001 | 4 | FlatList performance tuning on real device. |
| MOB-002 | 4 | Image caching and memory profiling on mobile. |
| MOB-003 | 4 | Offline database, sync and conflict-resolution UX. |
| MOB-004 | 4 | Background/resumable uploads on iOS/Android after mobile scope is active. |
| MOB-005 | 0/4 | Verify permission strings if mobile release is still intended; otherwise mark deferred. |
| MOB-006 | 4 | App-store readiness audit after a supported mobile build exists. |

### DevOps / CI / infrastructure
| Issue | New phase | Action / disposition |
|---|---|---|
| OPS-001 | 3 | Harden cloud Dockerfiles, multi-stage build and non-root runtime. |
| OPS-002 | 0 | Add/reuse dependency caches only if they reduce total CI time/cost. |
| OPS-003 | 3 | Supabase migration rollback test in a disposable/test project. |
| OPS-004 | 3 | Export OpenAPI artifact from the active cloud API build. |
| OPS-005 | 4 | DevContainer + seeded docker-compose for contributors. |
| OPS-006 | 4 | ADRs for material architecture decisions. |
| OPS-007 | 0/3 | CODEOWNERS/release checklist when team ownership and release process exist. |
| OPS-008 | 4 | Evaluate Nx/Turborepo only if repo scale demonstrates need; optional. |
| OPS-009 | 0 | Inventory legacy code references, then archive safely without breaking local startup. |

### Testing & QA
| Issue | New phase | Action / disposition |
|---|---|---|
| QA-001 | 1/3 | Establish honest coverage baseline; enforce thresholds only after baseline is measured. |
| QA-002 | 3 | OpenAPI contract tests for active cloud API/frontend contract. |
| QA-003 | 3 | k6 load tests for cloud API after staging/runtime is available. |
| QA-004 | 4 | Chaos drills for worker/DB/network only where infrastructure exists. |
| QA-005 | 0/1 | Identify flaky tests, quarantine with issue tracking; do not hide real failures. |

### Code quality
| Issue | New phase | Action / disposition |
|---|---|---|
| CQ-001 | 4 | Detect/refactor circular dependencies in active packages. |
| CQ-002 | 0/1 | Replace silent catches with structured diagnostics and privacy-safe reporting. |
| CQ-003 | 0/4 | Remove dead code only after active/deferred boundaries and references are proven. |
| CQ-004 | 1/4 | Consolidate duplicate UI only when it reduces active-code maintenance risk. |

## 5. Existing Phase A–E work carried forward

- **Old Phase A (security):** implemented foundations are retained; npm/Dependabot and lint debt remain open; re-verify auth/logout and current security boundaries.
- **Old Phase B (local workflow):** core code is present; real browser workflow acceptance remains required.
- **Old Phase C (OCR/search):** implementation and resource guards are present; representative Myanmar/English quality remains unverified.
- **Old Phase D (pilot):** harness exists; target-machine copied-office-data pilot is still a hard release gate.
- **Old Phase E (enterprise/cloud):** remains separate/deferred; cloud auth/storage foundation exists but real authenticated E2E and cross-user isolation remain open. No production reactivation is authorized by this roadmap.

## 6. Immediate execution order

1. Inspect and reconcile the Phase 1 code/tests for local auth, organization apply/undo, OCR limits, pilot output schema and frontend session-state reset.
2. Update the canonical status document so completed code, verified evidence, pending proof and deferred work are clearly distinguished.
3. Fix only confirmed regressions or mismatches found in that inspection.
4. Triage dependency/Dependabot/lint findings without blind upgrades or extra CI workflows.
5. Prepare the real-machine pilot checklist and run it only against a copied dataset on the target machine.
6. After Phase 2 evidence, decide which cloud remediation items are genuinely in scope.

## 7. Verification and release evidence

For each task, record: issue ID, changed paths, reason, tests actually executed, result, risks/rollback, and whether evidence is code-level, CI-level, live-service or real-machine.

Required gates:
- Focused backend tests for each changed service.
- Frontend smoke/build checks for UI changes.
- Security boundary regression tests for source paths, sessions, restore and approval.
- Real browser acceptance for complete workflows.
- Real copied-data pilot for Phase 2.
- Two-user authenticated E2E for Cloud phase.
- Staging-only DAST/load/chaos tests when a safe staging environment exists.

A skipped/unavailable test is recorded as **not run**, never as passed. A deployment-ready code change is not the same as an approved production deployment.


## 8. Execution log and evidence boundary

### 2026-10-03 — Phase 1 security/configuration batch

Implemented in the repository:
- **SEC-002:** `web-platform/backend/app/main.py` now parses CORS as an explicit HTTP/HTTPS origin allowlist, rejects wildcard origins, credentials embedded in origins, paths, query strings, fragments, invalid ports and empty allowlists, and removes duplicate origins.
- Added focused CORS regression cases in `web-platform/tests/test_cors_config.py`.
- **Local auth boundary:** expanded `web-platform/tests/test_local_auth.py` to assert that refresh, identity (`/me`) and logout endpoints are denied in production, `prod` and staging environments, complementing the existing login/workspace denial coverage.
- **Personal Local build contract:** documented `VITE_DOKA_EDITION=personal-local` for production-built local frontend, the backend `ENVIRONMENT=local|development` requirement, and the Supabase/local-auth separation in `web-platform/frontend/.env.example` and `web-platform/README.md`.
- **FE-008 / workflow state:** `WorkspaceReview.tsx` now clears prior search/OCR results, drafts, proposals and approvals before scan/OCR/plan requests; starting a new import also clears previous session search results. Frontend smoke assertions cover these reset boundaries.
- **Organization/OCR concurrency:** planning, document understanding and OCR correction writes now use the same per-session lock as scan, apply and undo, preventing those session mutations from racing each other in the local process.
- Local bootstrap-password verification now uses constant-time comparison.
- **OCR test/runtime dependencies:** added `numpy` and `opencv-python-headless` to `web-platform/backend/requirements-local.txt`, because the active OCR module imports both at module load and the backend test workflow installs this local profile.
- **SEC-013 / Service Worker privacy:** `web-platform/frontend/public/sw.js` now bypasses caching for non-GET requests, requests with Authorization, cross-origin requests, all query-string URLs, and `/api`/`/auth` paths; only app-shell and same-origin `/assets/` requests are cacheable. Added frontend smoke assertions for these boundaries. Test execution remains pending.
- **SEC-003 / SEC-004 audit note:** active Personal Local `Settings._validate()` already enforces explicit production `SECRET_KEY`, minimum 32-byte signing key, and source read-only flags at settings initialization; `/api/config` exposes only edition/boolean configuration and no filesystem paths. This is code inspection, not a runtime test.
- **SEC-003 / production alias correction:** `ENVIRONMENT=prod` is now normalized to `production` before validation, production/staging default `DEBUG` to false, and explicit `DEBUG=true` is rejected in production. Added focused unit tests; execution remains pending.
- **OCR result schema:** document understanding now records `extraction_method="ocr"` separately from detected `language` (`mya`, `eng`, `mya+eng`); a focused regression test was added. This aligns pilot reporting with the actual output schema.

Evidence status:
- GitHub accepted the file commits; this confirms repository writes only.
- The new/affected tests have **not been executed** in this work batch. No passing-test claim is made.
- No GitHub Actions workflow was dispatched or rerun. No Vercel deployment or activation was performed.
- Local token revocation and refresh replay state now use a dedicated SQLite file outside `WORKING_ROOT`; access and refresh tokens share a session-family ID so logout revokes rotated tokens too. Process-restart and refresh replay regression tests were added, but have **not been executed** yet.
- Organization Apply/Undo, OCR limits, pilot schema and frontend session reset were inspected in source; their full test suites and browser/pilot acceptance remain pending execution.

Next Phase 1 work:
- Execute the new durable token-state, session-family logout, cross-environment endpoint and CORS regression tests; inspect the SQLite state file permissions and backup/restore implications on the target OS.
- Execute focused backend tests and frontend smoke/build checks in a suitable local environment; record exact commands/results.
- Continue confirmed frontend accessibility/effect-cleanup and organization/undo edge-case audit before declaring Phase 1 accepted.


### CI observation — 2026-10-03

- Latest observed automatic Doka Quality Checks run: `37107344383` for commit `82dfff5`. GitHub reports all three jobs (frontend checks, backend regression tests and backend dependency audit) as failed. The earlier inspected run `37107238360` exposed empty step lists and `BlobNotFound` logs; no usable diagnostic steps/logs have been returned, so the failure remains insufficient to attribute to the code or to claim the tests ran.
- Do not manually rerun or dispatch Actions solely to investigate this; keep the failure classified as **CI evidence unavailable/inconclusive** until GitHub exposes actual steps/logs or a local test environment is available.


### 2026-10-03 — SEC-014 legacy backup command hardening

Implemented in the repository:
- **SEC-014:** extracted PostgreSQL backup argument construction into `web-platform/backend/app/core/backup_utils.py`. It parses PostgreSQL URLs structurally (including percent-encoded credentials, IPv6 hosts and explicit ports), validates required connection fields, supplies passwords only through the child-process environment, and builds an argument array for `pg_dump` without shell interpolation.
- Updated the legacy Celery `backup_database` task to use the helper and invoke `pg_dump` with `--no-password`, captured output and no shell.
- Added focused parser/argument tests in `web-platform/tests/test_backup_utils.py`.

Scope and evidence boundary:
- The Personal Local FastAPI entry point does not register the legacy admin/Celery backup route; Personal Local workspace backups remain handled by `WorkspaceBackupService`. This SEC-014 change hardens the retained legacy database-backup task, not the active Personal Local workspace archive flow.
- Tests have **not been executed**. GitHub file commits confirm repository writes only.
- **BE-009:** the inspected `VersionService` is part of the legacy ORM/cloud route stack and is not loaded by the Personal Local entry point. Its read-modify-write version allocation remains a deferred cloud concurrency issue; do not treat it as a Phase 1 local blocker or claim it fixed.
- **BE-010:** the active `SafeWorkspaceService` inspected here has per-session lock creation and no separate lock-status/duplicate-return function in the inspected implementation. The originally described duplicate-return cleanup could not be matched to an active code path; retain as needs-source-location clarification rather than making a speculative change.
- **SEC-001:** secret scanning remains open. No unreviewed third-party workflow action or unvalidated baseline was added; integrate scanning only after selecting a reproducible scanner and establishing the baseline.

### 2026-10-03 — Phase 0–3 implementation follow-up

Implemented in repository source (execution verification pending):
- **BE-001:** bounded streaming and cleanup were added to the retained legacy upload route. It is not mounted by the current Personal Local or Cloud API entry points, so active cloud multipart/resumable upload remains open.
- **BE-009 / BE-011:** the legacy file-based version service now serializes create/delete per document, writes metadata atomically, and raises a diagnostic on unreadable history instead of returning an empty list. Added concurrency and corrupt-metadata tests; this service remains separate from the Personal Local workspace service.
- **BE-010:** removed the unreachable duplicate return in the legacy document lock-status route.
- **SEC-002:** cloud API CORS now rejects wildcard/malformed credentialed origins and allows authenticated DELETE; focused tests added.
- **SEC-005 / AI-001:** external embedding calls require AI enabled plus explicit external-processing consent; OCR/document analysis is wrapped as JSON untrusted data under trusted task instructions. Configurable AI input length cap added with regression tests.
- **FE-001 / FE-004:** ThemeContext now handles unavailable browser storage safely, memoizes context values, and subscribes/unsubscribes to system theme changes; frontend smoke assertions added.
- **SEC-006 / SEC-007:** consolidated quality workflow now includes CodeQL, report-only Semgrep baseline artifact, and SPDX SBOM artifact.
- **SEC-011:** source-level Supabase RLS/grant/storage review documented in docs/DOKA_SUPABASE_SECURITY_REVIEW.md.

Not complete / external verification still required:
- CodeQL/Semgrep/SBOM workflow has not produced an observed run result. Semgrep remains report-only pending baseline triage; branch protection/ruleset enforcement is not verified.
- OWASP ZAP DAST requires an approved staging URL, safe test credentials and explicit target scope; do not scan the paused production site.
- Live Supabase RLS/grant state and two-user isolation need an authorized live-project audit. The current Worker audit write is best-effort, not transactionally guaranteed.
- Dependabot alerts still need an itemized inventory and per-advisory dispositions. Manifest/lock consistency is not a vulnerability audit.
- Phase 1/2 local browser workflow, OCR acceptance, source hash invariance, restore drill and copied-office pilot remain pending.
- Phase 2/3 cloud E2E, AI budget enforcement, Vault/KMS, production worker/Redis/CDN/WAF and other provisioned infrastructure cannot be marked complete from repository edits alone.

Evidence boundary:
- New tests were added but **not executed**. No passing-test claim is made.
- No workflow was manually dispatched or rerun; Vercel production remains paused/off and no source data was accessed.

### 2026-10-03 — Mobile prototype audit and bounded fixes

- **MOB-005:** added purpose-specific iOS camera/photo-library permission descriptions and Android camera/image permission declarations in mobile/app.json; generated native manifests and actual device prompts still need iOS/Android builds and real-device verification.
- Fixed the missing useEffect import and unsafe startup session flicker in the mobile AuthContext; added best-effort remote logout before local SecureStore cleanup.
- Corrected Expo picker result normalization and React Native multipart file descriptors; added MIME inference for legacy single-asset picker results and aligned upload result shape with the screen. Axios client is memoized and the API base is configurable through EXPO_PUBLIC_API_BASE_URL.
- Added pure Node tests for picker normalization and app permission declarations. An isolated Node 22.16 harness for the nine assertions passed; this does not verify Expo bundling, native builds or device upload behavior.
- **MOB-004:** not implemented as resumable upload. The server has no multipart upload session/part/commit API or background task contract; a client retry alone would restart from byte zero. Keep blocked until the selected edition's authenticated upload API is designed and tested.
- **MOB-002:** image caching is not introduced because the current mobile UI has no private document image preview. Define signed-URL expiry, authorization, cache encryption/eviction and logout purge before adding any private-image cache.
- The app remains a legacy Expo SDK 50 / React Native 0.73 prototype with no lockfile and an API contract that does not match either active Personal Local or Cloud API entry point. Do not claim mobile Phase 3 release readiness; coordinate SDK upgrade, API adapter, E2E and store review first.

### 2026-10-03 — Phase 2–3 operations and QA follow-up

- **OPS-001:** hardened the retained production Dockerfile to multi-stage Python 3.12, non-root runtime, minimal runtime libraries and health check; added .dockerignore to exclude environment secrets and local/private data. Image build remains unverified.
- **OPS-004 / QA-002:** added a reproducible Cloud API OpenAPI exporter and CI artifacts for OpenAPI JSON and backend coverage XML. Coverage is report-only until a real baseline exists; no threshold is guessed.
- **DR-003:** added a Personal Local backup/restore drill procedure with manifest/hash validation, separate recovery destination and RTO/RPO approval gate. Actual restore evidence remains pending.
- RTO/RPO targets, immutable/offsite backups, Vault/KMS, Redis/high availability, WAF, DAST staging, production load tests and live cloud controls remain provisioning/owner-verification gates rather than repository-complete work.

### CI evidence update — 2026-10-03

- Automatic push run 37114338756 for commit 0babf061fea1f2a3e40f7ead9bbc7262e572cac8 reports all four jobs failed, but every job record has steps=null and logs_url=null. No test, audit, CodeQL, Semgrep or SBOM command output is available.
- The run was automatic; no workflow_dispatch or manual rerun was used. Classify this as runner/log evidence unavailable, not a confirmed code failure or a passing verification.

### SEC-001 follow-up — 2026-10-03

- Added a pinned Gitleaks pre-commit hook matching the CI version and documented setup. Historical Git-history scanning and itemized GitHub Secret Scanning/Dependabot alert review remain pending; no baseline is declared clean.

### Latest CI evidence — run 37114518007

- The automatic run for the latest code commit has all four jobs marked failed but exposes no steps or logs. This remains an infrastructure/evidence blocker, not an attributed code failure or a passing verification.

### 2026-10-03 — Local baseline and Safe Workspace read/write race

- A disposable loopback UI smoke test used one synthetic text fixture with `ORIGINAL_READ_ONLY=true` and `ALLOW_SOURCE_WRITE=false`. Its source SHA-256 was `4904B0500240FB28CA33A367D1CD65E8A67978228B5F51E7B878208C10FA1F7E`; all 28 generated working copies matched it. No office/source data was used.
- The smoke exposed concurrent status/list reads during `status.json` replacement on Windows: `Path.replace` raised `WinError 5`, and one polled status request returned HTTP 500. The smoke also issued 28 import POSTs; why the repeated requests occurred is unconfirmed. The full browser workflow was not completed.
- **BE-009 (Personal Local):** status, list, search, inventory, and understanding JSON reads now share the existing per-session lock with mutations. Added concurrent-reader regression cases for all five service paths. This is an in-process synchronization fix; multi-process locking and crash recovery remain unverified.
- After the fix, a controlled FastAPI TestClient HTTP walkthrough passed health, import/status/list, scan, local understanding, plan, explicitly confirmed apply, backup/verification, isolated Recovery restore, and undo using a synthetic fixture. The fixture source hash remained unchanged. This used a test-only auth dependency override; it is not real-browser or local-login acceptance.
- Verification: `.venv\Scripts\python.exe -m pytest ..\tests -q` from `web-platform\backend` — **154 passed, 8 skipped**, exit code 0. Ten warnings were deprecations (FastAPI `on_event` and legacy `datetime.utcnow`); no test failures.
- The active Personal Local real-browser/login acceptance gate remains pending; the API-level workflow passed after a test-only dependency override. Frontend checks and mobile utility tests passed earlier in this local session; `npm audit` still reports five high findings and no dependency upgrade was made.
- Source was unchanged by the smoke test; the fixture and temporary workspace were isolated under the OS temp directory. No commit, push, deployment, or manual GitHub Actions run was made.
