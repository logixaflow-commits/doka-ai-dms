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
A legacy Playwright-style E2E file exists at web-platform/backend/tests/test_e2e.py, but it targets an older username/password UI contract and legacy fixtures. No current Playwright dependency/runtime aligned to the Personal Local release flow was available in the accessible test environment.

Required scenario: login -> import -> scan/OCR -> review -> approve -> Final copy -> backup -> isolated restore -> undo, with source SHA-256 unchanged before/after.

## Gate 5 — Copied-office pilot
The repository contains scripts/doka_pilot_check.py and source snapshot/hash logic. Existing evidence is synthetic only. No representative copied-office pilot was run in this close-out pass.

Required evidence: copied data only, source SHA-256 before/after, import verification, scan/OCR result, organization review/approval, backup SHA-256, isolated Recovery manifest comparison and cleanup.

## Gate 6 — Backup/restore
Synthetic TestClient/backup evidence exists in the historical record, including successful backup verification and isolated Recovery restore with unchanged synthetic source. No real-machine timed drill was run.

Required real evidence: full backup -> destroy/disposable workspace -> restore -> integrity comparison, with backup size, file count, backup duration, restore duration, RTO and RPO recorded.

## Cloud acceptance
Use authenticated sessions and at least two distinct users for ownership isolation. Test 50 MiB boundary, signed URLs, version restore, Trash/permanent-delete behavior and provider cleanup/recovery.

Gate 9 remains PENDING because a live unauthenticated Worker probe returned HTTP 403 and no disposable authenticated test session was available.

Gate 10 remains PENDING because live Supabase health/migrations are verified but no two real authenticated test users were available. Synthetic RLS probes are not a substitute for two-user evidence.

Gate 11 remains PENDING because Cloudinary provider-level recovery passed, while B2 and Google Drive live evidence is unavailable.
