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

These results prove automated/code-side behavior only. They do not prove real browser, office-data, provider recovery or production isolation.

## Personal Local acceptance
Use representative copied data only. Verify source hashes before/after, import SHA-256, OCR quality, duplicate/version review, organization copy-only behavior, backup checksum, isolated restore and undo.

## OCR benchmark
Measure Myanmar/English representative samples and record CER/WER or the repository's accepted benchmark metrics. A benchmark pass must not be inferred from the presence of Tesseract.

## Cloud acceptance
Use authenticated sessions and at least two distinct users for ownership isolation. Test 50 MiB boundary, signed URLs, version restore, Trash/permanent-delete behavior and provider cleanup/recovery.

## Test isolation
Future durable test infrastructure should use an isolated backend database/fixtures rather than shared production data.
