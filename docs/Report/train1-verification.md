# Train 1 Contract Verification

**Date:** 2026-10-09  
**Scope:** Read-only code and targeted test verification. No application source files were changed. Pytest temporary state was directed to `D:\Doka\Train1VerificationTemp`.

## Result

**5 of 8 checklist items are confirmed by the targeted tests. The other 3 are partial and need follow-up evidence or integration.** The test runs produced 89 passed, 1 failed, and 1 skipped test in total. The failure reproduced in three additional runs and is described under item 1.

| # | Checklist item | Status | Evidence and limitation |
|---|---|---|---|
| 1 | Durable job idempotency | **Partial** | Cloudflare D1 job-ledger tests pass for idempotent creation, key/payload binding, and job transitions. These use a fake D1 binding; the SQLite schema tests verify constraints offline, not a live Cloudflare D1 deployment. Separately, the file-backed local store's concurrent-claim test failed on Windows in the main run and all three repeats (`PermissionError` during `os.replace`). Its implementation documents a POSIX-only lock; this Windows result does not establish that the D1 implementation fails. |
| 2 | Retryable / non-retryable taxonomy | **Pass (contract tests)** | Shared taxonomy tests and outbox tests pass for retryable, non-retryable, and conservative handling of unknown errors. The outbox has its own classifier rather than calling the shared helper, so the policies are tested in parallel, not enforced through one shared implementation. |
| 3 | Retry exhaustion + DLQ | **Pass (contract tests)** | Job, outbox, and shared-contract tests pass for exhausted attempts and dead-letter/dead terminal states. D1-specific tests use fake bindings; there was no live queue/D1 integration run. |
| 4 | Provider circuit breaker | **Pass** | Shared tests cover closed/open/half-open/recovery. Provider-boundary tests also verify that repeated failures are skipped and a successful recovery closes the circuit. |
| 5 | Failover safety | **Pass** | The unified AI service gates alternate-provider failover on explicit approval; contract and provider-fallback tests pass for approved and unapproved paths. |
| 6 | Exact-scope consent boundary | **Partial** | The shared consent helper test passes for subject, purpose, and exact resource scope. The active unified AI service instead checks a global external-processing-consent setting; the exact-scope grant helper is not wired into that provider-call boundary. |
| 7 | Structured AI output | **Pass** | Contract tests pass for required fields and rejection of unknown fields. The provider-boundary test also confirms invalid provider analysis output is rejected. |
| 8 | Myanmar/English + OCR | **Partial** | The bilingual retrieval contract and OCR safety tests pass. The isolated two-scan English and Myanmar/English pilot/browser workflow passed, but the broader benchmark scored Myanmar/English CER 79.94% and WER 171.43%, with its reference not visually verified. The full copied-office pilot had three OCR timeouts. This is not a full OCR-quality or full-office acceptance pass; see [personal-local-acceptance-report.md](./personal-local-acceptance-report.md). |

## Follow-up remediation — 2026-10-11

The repository follow-up has since corrected two code-side findings from this historical read-only report:

- **Windows local idempotency lock:** added `msvcrt` byte-range locking as the Windows fallback and a regression test for lock/unlock behavior. Python compilation and a disposable 100-way concurrent-claim smoke test passed; the full focused pytest suite is tracked by current CI.
- **Exact-scope provider consent:** the unified AI service now requires a granted `ConsentGrant` matching subject, purpose, and exact resource scope at provider-fallback and embedding entry points. Missing or mismatched grants fail closed. This is not yet end-to-end consent completion: application consent persistence and trusted caller propagation still require integration evidence, so affected callers without grants remain blocked from external processing.
- **OCR quality gate:** benchmark gate readiness now includes scored samples for required languages and per-language-label mean CER/WER thresholds (defaults 0.30/0.60). The latest six-sample report was corrected to `gate_ready=false` because its Myanmar/English result exceeds both limits. Visual verification of the Myanmar reference and a new representative benchmark remain required.

These fixes do not change the historical results below; they are follow-up changes with new commits and CI evidence tracked separately.

## Verification runs

1. Targeted contracts: `test_job_idempotency.py`, `test_train1_safety_contracts.py`, `test_ai_provider_boundaries.py`, `test_ocr_safety_limits.py`, `test_cloudflare_jobs.py`, `test_cloudflare_outbox.py`, and `test_unified_ai_fallback.py` — **64 passed, 1 failed, 1 skipped**.
2. D1 SQLite schema and adapter contracts: `test_cloudflare_d1_schema.py` and `test_cloudflare_d1_adapter.py` — **25 passed**.
3. Repeated `test_concurrent_duplicate_claim_only_creates_one_record` three times on Windows — **failed all three times** with a file replacement/locking error.

The skipped test is the OCR symlink-input test because symlink creation was unavailable in this Windows environment. These results are local contract/unit evidence only; they do not substitute for live Cloudflare D1/queue integration or full-data OCR acceptance.
