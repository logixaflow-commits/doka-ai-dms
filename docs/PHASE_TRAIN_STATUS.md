# Doka Phase Train Status

This is the operational sequence after the Personal Local + Cloud acceptance
harness is merged into `main`. **`main` is the source of truth. Do not create a
feature branch for routine phase work.** A phase may use isolated disposable
runtime environments for acceptance, but repository changes land directly on
`main` after validation.

## Operating rule

Phases are **sequential trains**, not one mixed backlog. Inside the active train,
independent workstreams may run in parallel:

1. contract + threat model
2. implementation
3. unit/contract/security tests
4. migration + rollback
5. performance/cost baseline
6. disposable acceptance evidence
7. activation

A later train does not activate while the previous train's exit evidence is
missing. Preparatory documentation/tests for later trains may be added early,
but must not be presented as activated functionality.

## Train 0 — Release Evidence Closure

**Exit:** Gates 3–12 have real evidence; Gate 12 release claim is allowed.

Parallel tracks:
- Local: Tesseract `mya`/`eng` → copied-office pilot → recovery timing → browser E2E.
- Cloud: authenticated User A/B E2E → RLS isolation → provider recovery.
- Security: dependency/secret review + Supabase security warnings.
- Release: evidence evaluator + final freeze.

Current blockers are runtime/environmental, not missing acceptance harness code.
Do not mark a gate PASS from code or CI alone.

### Current Train 0/parallel-prep state
- Acceptance preflight exists and reports missing local/cloud capabilities without recording secrets.
- Gate 9/10 evidence mapping accepts the privacy-safe User A/B isolation assertion from the cloud runner.
- Live Supabase RLS has been inspected; the leaked-password-protection warning remains a security-freeze blocker until the platform setting is resolved.
- Real Tesseract, copied-office, recovery, authenticated cloud, and provider-recovery evidence remain runtime prerequisites.
- Train 1 workflow/AI foundations are being hardened in parallel, but are not activated as a release claim.

## Train 1 — Phase 7/8 Workflow + AI Hardening

**Exit:** durable workflow/idempotency/retry evidence, provider failover evidence,
multilingual retrieval benchmark, and human-approval safety path.

Parallel tracks:
- workflow state/idempotency
- provider routing/circuit breaking
- multilingual retrieval/OCR-aware ranking
- AI safety and approval boundaries

## Train 2 — Phase 9 Controlled Product Expansion

**Exit:** two-tenant/two-user authorization matrix, clean RLS review,
storage isolation, invitation expiry/replay evidence, rollback-tested membership migration.

Parallel tracks:
- organization lifecycle/RBAC
- API/database authorization
- storage isolation
- invitations/session invalidation

## Train 3 — Phase 10 Scale & Reliability

**Exit:** duplicate delivery, worker takeover, bounded retry/DLQ, load baseline,
and disposable restore drill evidence.

**Safety boundary:** do not enable late acknowledgements/worker-takeover behavior
until the affected jobs have a durable idempotency contract. Otherwise a worker
crash can convert safe redelivery into duplicate side effects. The implementation
must therefore land as one tested unit: idempotency key + durable state transition
+ late-ack/takeover policy + duplicate-delivery test.

Parallel tracks:
- queue/lease/idempotency
- observability/DLQ
- capacity baseline
- disaster recovery

## Train 4 — Phase 11 Advanced Intelligence

**Exit:** multilingual RAG benchmark, provenance completeness,
abstention/hallucination test, provider quality/cost/latency comparison.

Parallel tracks:
- retrieval/indexing
- reranking/evaluation
- provenance
- provider evaluation

## Train 5 — Phase 12 Enterprise / Mobile / Multi-region

**Exit:** mobile offline/resume matrix, region residency, regional outage,
restore/failback, enterprise audit/export evidence.

## Train 6 — Phase 13 Ecosystem / API Platform

**Exit:** versioned API compatibility, signed webhook replay/forgery matrix,
client quota/deprecation evidence, integration sandbox acceptance.

## Train 7 — Phase 14 Intelligent Operations

**Exit:** injected failure → alert → diagnosis → mitigation → recovery evidence,
with SLOs and escalation policy.

## Train 8 — Phase 15 Data Intelligence

**Exit:** lineage completeness, retention/purge verification,
privacy-safe aggregation, export/import round trip.

## Train 9 — Phase 16 Global Platform

**Exit:** regional configuration matrix, localization/timezone/currency checks,
cross-region isolation and recovery evidence.

## Train 10 — Phase 17 Ecosystem Scale

**Exit:** tenant-scoped integration credentials, quotas, revocation,
capability discovery and sandbox evidence.

## Train 11 — Phase 18 Continuous Reliability / Governance

**Exit:** dependency lifecycle closure, security/chaos drills,
rollback rehearsal, quarterly recovery evidence, signed release evidence.

## Main-first change discipline

- Do not create another long-lived feature branch for these trains.
- Keep changes small enough to validate immediately on `main`.
- Never weaken an acceptance gate to make a train appear complete.
- Runtime secrets/tokens stay outside git and evidence files.
- Evidence files record assertions and timing only; never OCR text, credentials,
  user emails, or full source paths.


## 2026-10-08 execution checkpoint
- Train 0 disposable runtime preflight was executed in a clean ephemeral Python box: Python 3.13, Node 22, npm 10 and Playwright 1.64 were available; Tesseract and the required Python runtime modules were not. The preflight correctly returned not-ready and recorded no secrets, OCR text or paths.
- Train 1/3 workflow contract hardening is now on `main`: explicit idempotency keys, per-instance POSIX file locking, atomic/fsynced instance replacement, replay-safe duplicate delivery and regression coverage.
- The targeted workflow suite was executed in the disposable runtime: **6 passed**. This is contract/runtime evidence for the workflow change, not a full backend-suite claim.
- The late-ack/worker-takeover boundary remains closed until external step side effects have their own durable idempotency semantics.


## 2026-10-08 parallel execution checkpoint — Train 0 + Train 1/3 + forward preparation

### Train 0 live/provider observations
- Supabase Security Advisor was rechecked live. `auth_leaked_password_protection` remains WARN and is still a release/security-freeze blocker.
- Cloudflare Workers live inspection confirmed Worker `doka-ai-dms` exists and currently has a 100% deployment on version 602. This is deployment evidence only; it is not application acceptance evidence.
- Cloudflare currently reports 602 versions and 603 deployments; no rollback or traffic change was performed during this audit.
- OCR/browser/cloud/provider acceptance remains evidence-gated and is not promoted to PASS without the required runtime/data/credential evidence.

### Train 1/3 hardening boundary
- Workflow idempotency and atomic instance persistence are implemented and targeted-runtime verified.
- Durable job-level idempotency state contract is now implemented and contract-tested on `main`: claim binding, atomic persistence, duplicate convergence, retry exhaustion and DLQ transition. The queue adapter is intentionally not wired yet; distributed takeover remains closed until the durable ledger is backed by the production job/DB layer and external side effects share the key.
- Train 1 safety contract layer is now implemented/tested: conservative retry taxonomy, exhaustion/DLQ records, circuit breaker closed/open/half-open transitions, explicit failover approval, exact consent scope, fail-closed AI output schema, mya/eng retrieval identity/hash/language checks, and human-approval boundary. These are transport/provider agnostic and do not enable worker takeover.
- Train 1 concrete integration is now partially wired: the Cloudflare D1 `jobs` ledger enforces durable idempotency-key binding/replay, the D1 outbox applies retryable/non-retryable failure handling, the unified AI router uses the shared retry taxonomy/circuit breaker and requires explicit failover approval, and retrieval now normalizes OCR text and language-scopes Myanmar/English ranking.\n- Remaining Train 1 work is runtime evidence plus any concrete side-effect/consumer wiring discovered during acceptance. Worker takeover/late acknowledgement remains disabled until Train 3.
- AI provider work remains contract-first: half-open circuit behavior, failover safety, consent boundary and output schema tests before activation.

### Forward train preparation (not activated)
- Train 2: organization lifecycle, RBAC/tenant matrix, RLS/storage isolation, invitation/session replay controls, migration rollback contract.
- Train 3: queue lease/takeover, duplicate delivery, bounded retries/DLQ, load/failure-injection and restore-drill contracts.
- Train 4+: retain phase-by-phase contracts and rollback/acceptance gates; implementation/activation remains sequential.


### 2026-10-08 Train 1 concrete-integration checkpoint
- D1 durable job adapter added at `cloudflare_worker/jobs.py`, using the existing authoritative `jobs.idempotency_key` uniqueness and bounded attempt fields. It supports create-or-converge, pending claim, success, retryable failure, non-retryable failure and exhaustion → dead transitions. It does not implement lease takeover.
- D1 outbox delivery now distinguishes transient failures from permanent/schema failures; permanent failures go directly to `dead` and transient failures retain bounded exponential backoff.
- Unified AI provider routing now uses the Train 1 retry taxonomy and circuit-breaker state machine. Provider failover is explicitly opt-in through `AI_PROVIDER_FAILOVER_APPROVED=true`; without it, a provider outage does not silently broaden external data processing.
- Retrieval now canonicalizes OCR text to Unicode NFC, records SHA-256 retrieval identity, validates supported `mya`/`eng` language metadata, scopes ranking by language, and avoids the English-centric embedding path for Myanmar OCR.
- These are implementation/contract changes, not live provider/runtime PASS claims. Acceptance still requires real D1/Worker, AI-provider, and Myanmar/English benchmark evidence.


### CI reconciliation — 2026-10-08
- Latest implementation commit `06f6874aa999fec441bbb285327a17af795625c2` has **Doka Quality Checks: SUCCESS** and **CodeQL: SUCCESS**.
- The successful Quality run included the concrete Train 1 regression tests; cloud storage contract tests also passed.
- Remaining Train 1 exit work is live/runtime evidence and any provider/queue consumer paths that require real credentials or infrastructure. No production PASS is claimed from CI alone.
