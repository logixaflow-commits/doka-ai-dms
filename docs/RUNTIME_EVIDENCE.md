# Doka Runtime Evidence

This document records disposable-runtime observations that are useful for release decisions. It is intentionally privacy-safe: no credentials, OCR text, source paths or user identities are recorded.

## 2026-10-08 — disposable runtime checkpoint

### Train 0 preflight
- Runtime: ephemeral Python container.
- Python: 3.13 available.
- Node: 22 available.
- npm: 10 available.
- Playwright: 1.64 available.
- Tesseract: **absent**.
- Myanmar/English Tesseract languages: therefore unavailable.
- Required backend Python modules for the full acceptance harness were not installed in the clean box.
- acceptance_preflight.py in local mode returned not-ready (exit 2).
- Attempted system installation of Tesseract was blocked by the unprivileged runtime; no repository state was changed.

### Train 1/3 workflow contract
- workflow_automation.py was hardened with an explicit bounded idempotency key, per-instance POSIX locking, atomic replacement plus fsync, and replay-safe duplicate handling.
- Targeted workflow runtime suite: **6 passed**.
- Covered: normal completion, wrong assignment/step, next-step failure propagation, invalid idempotency key, key reuse conflict, and concurrent duplicate delivery.
- Full backend suite was not claimed; this is targeted contract evidence only.

### Durable job-level idempotency contract checkpoint
- `job_idempotency.py` now provides a transport-agnostic durable state machine for claim → running → retryable/exhausted → dead-lettered or succeeded.
- Contract tests cover duplicate claim convergence, key-to-job binding, retry exhaustion/DLQ, terminal replay safety, concurrent duplicate claims, and explicit absence of takeover/lease APIs.
- No queue worker or late-ack/takeover path was enabled by this change.

## Release interpretation

Train 0 remains **PENDING** for OCR/browser/pilot/recovery/cloud/provider evidence. The runtime result is a real blocker, not a missing harness feature.

Train 1/3 contract hardening may continue in parallel, but distributed late-ack/worker takeover must remain disabled until external side effects use a durable idempotency contract at the job/DB layer.


## 2026-10-08 — second live/provider checkpoint

- Supabase Security Advisor still reports `auth_leaked_password_protection` as WARN. No Auth setting mutation was available through the connected tool, so no unverified remediation is claimed.
- Cloudflare account inspection found the live `doka-ai-dms` Worker with version 602 at 100% traffic. The latest deployment was created 2026-10-08 and was not modified during this audit.
- Cloudflare version/deployment inventory is provider evidence only; it does not replace authenticated application E2E, storage recovery, or browser acceptance evidence.
- No B2 or Google Drive live recovery evidence was produced in this pass.

- Train 1 safety contracts are focused contract evidence only; no external provider call or production queue integration is claimed.


## 2026-10-08 Train 1 CI evidence
- Latest main commit: 06f6874aa999fec441bbb285327a17af795625c2
- GitHub Actions **Doka Quality Checks: SUCCESS**.
- GitHub Actions **CodeQL: SUCCESS**.
- Quality run included backend regression, cloud storage contracts, symlink security, dependency audits, static/SBOM checks, frontend lint/build/smoke tests and the newly added Train 1 regression coverage.
- The cloud storage contract job passed after the Train 1 D1/outbox test integration was corrected.
- This CI evidence is repository/CI evidence only; it does not substitute for live D1, authenticated cloud A/B, provider recovery, OCR benchmark or browser acceptance evidence.


## 2026-10-08 Train 1 live-infrastructure reconciliation
- Cloudflare Worker `doka-ai-dms`: latest inspected version **631**, deployed **100%**.
- Worker `workers.dev` subdomain is enabled; account subdomain is `logixaflow`.
- Cloudflare D1 inventory: **0 databases**. Therefore live D1 job-ledger acceptance is **PENDING**, not PASS.
- D1 database creation was attempted through the connected API but blocked by the platform safety layer before mutation; no infrastructure mutation occurred.
- A privacy-safe live D1 acceptance runner is now committed at `scripts/d1_job_runtime_acceptance.py` for the moment a database is provisioned.
- Supabase security advisor still reports **Leaked Password Protection Disabled**; no supported in-chat Auth-setting mutation is available, so this remains a Train 0 security-freeze blocker.
