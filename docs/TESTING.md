# Doka Testing

> **Owner:** How is Doka tested from code-level checks through release acceptance?
> **Update when:** Test suites, acceptance criteria, benchmark methodology, CI evidence or release-test requirements change.
> **Last Updated:** 2026-10-08
> **Do NOT put here:** Product roadmap ownership, secrets, or deployment topology.

## Required layers
1. Syntax/static checks.
2. Maintained unit/regression suites.
3. Frontend lint/build/smoke.
4. Integration tests for changed boundaries.
5. Real browser acceptance when release-critical.
6. Copied-office pilot and real OCR benchmark.
7. Provider/recovery/isolation tests for Cloud release.

## Current recorded evidence
Latest recorded maintained Personal Local suite: 386 passed with 11 warnings. Frontend lint/build/smoke and quality/CodeQL workflows were recorded green.

This close-out pass could not rerun pytest in the accessible execution box because pytest and pip are not installed. Do not treat that environment limitation as a test failure or as fresh green evidence.

## Gate 3 — OCR
The repository contains scripts/ocr_benchmark.py and OCR regression tests. The current benchmark runner requires a copied sample directory plus a JSON manifest with reference text. The accessible test environment does not contain the required sample directory/manifest, and Tesseract is not installed there.

A historical privacy-scrubbed report contains 5 mixed mya+eng samples with mean CER 0.1660492282 and mean WER 0.3081550029, but it does not record the Tesseract version and is therefore not accepted as current Gate 3 release evidence.

Required owner evidence: representative Myanmar and English samples, manifest/reference text, Tesseract version, CER/WER report and privacy-safe evidence.

## Gate 4 — Personal Local browser
The repository now contains a current Playwright suite at web-platform/frontend/e2e/personal-local.spec.ts plus a dedicated config and stable UI selectors. The suite covers the Personal Local release flow and source immutability check. The browser runtime/data acceptance run remains pending.

Required scenario: login -> import -> scan/OCR -> review -> approve -> Final copy -> backup -> isolated restore -> undo, with source SHA-256 unchanged before/after.

## Gate 5 — Copied-office pilot
The repository contains scripts/doka_pilot_check.py with dedicated workspace/backup isolation, source before/after hashes, OCR checks, backup verification, and isolated recovery comparison. Existing evidence is still synthetic only; no representative copied-office pilot was run in this close-out pass.

Required evidence: copied data only, source SHA-256 before/after, import verification, scan/OCR result, organization review/approval, backup SHA-256, isolated Recovery manifest comparison and cleanup.

## Gate 6 — Backup/restore
Synthetic TestClient/backup evidence exists in the historical record, including successful backup verification and isolated Recovery restore with unchanged synthetic source. No real-machine timed drill was run.

Required real evidence: full backup -> destroy/disposable workspace -> restore -> integrity comparison, with backup size, file count, backup duration, restore duration, RTO and RPO recorded.

## Cloud acceptance
A dedicated runner now exists at `scripts/cloud_acceptance.py`. It requires two pre-created authenticated Supabase access tokens and never creates users or accepts service-role credentials. It exercises user-A upload/update/download, user-B list/download isolation, and optionally the exact 50 MiB upload boundary via `DOKA_CLOUD_50MIB_FILE`. The runner writes privacy-safe JSON evidence and returns non-zero until all required checks, including the 50 MiB fixture, pass.

Use authenticated sessions and at least two distinct users for ownership isolation. Test 50 MiB boundary, signed URLs, version restore, Trash/permanent-delete behavior and provider cleanup/recovery.

Gate 9 remains PENDING because a live unauthenticated Worker probe returned HTTP 403 and no disposable authenticated test session was available.

Gate 10 remains PENDING because live Supabase health/migrations are verified but no two real authenticated test users were available. Synthetic RLS probes are not a substitute for two-user evidence.

Gate 11 remains PENDING because Cloudinary provider-level recovery passed, while B2 and Google Drive live evidence is unavailable.


### Train 1 live D1 acceptance

Once D1 credentials are available in the runtime environment, the reusable runner can be executed again; the current live acceptance has already been recorded separately:

`python scripts/d1_job_runtime_acceptance.py --output Phase0_Evidence/train1/d1-job-runtime.json`

Current connector-side live acceptance passed and is recorded at `Phase0_Evidence/train1/d1-job-runtime.json`. Required environment presence is checked by `scripts/acceptance_preflight.py`:
`CLOUDFLARE_ACCOUNT_ID`, `CLOUDFLARE_API_TOKEN`, `DOKA_D1_DATABASE_ID`.

The runner is disposable and privacy-safe: it verifies duplicate idempotency convergence, terminal success, retry, and exhaustion/dead state, then attempts cleanup. It never records credentials, database IDs, test IDs, or payload contents.
