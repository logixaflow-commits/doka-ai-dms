# Local OCR Comparison & Verification

This adds a local-only comparison engine for the Personal Local workflow.

## Behavior
- PASS: verified reference and OCR output are within configured CER/WER thresholds.
- REVIEW: errors exceed the thresholds; compare the original scan and OCR text.
- FAIL: OCR output is empty or required reference/input is invalid.
- Differences are grapheme-aware so Myanmar combining marks are compared as clusters.
- Batch output includes per-file statuses and aggregate counts; partial success is not reported as full success.
- The engine performs no network calls and writes no files. A local UI can render the diff segments side by side.

## Limits and acceptance
A text match is only as trustworthy as the verified reference. Without a reference, OCR confidence/layout heuristics cannot prove correctness; a person must review the original. Critical fields (names, IDs, dates, amounts, document numbers) need separate checks. Keep source files read-only and compare hashes before/after the pilot.

This commit provides comparison logic and unit tests, not an integrated browser UI or a validated 1,000-file run. Do not mark Local release complete until the test suite, representative Myanmar/English benchmark, source-integrity check, and end-to-end review workflow pass.
