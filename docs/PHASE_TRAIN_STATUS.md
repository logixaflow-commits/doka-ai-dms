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
