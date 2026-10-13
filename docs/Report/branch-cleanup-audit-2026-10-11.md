# Branch Cleanup Audit — 2026-10-11

Repository: logixaflow-commits/doka-ai-dms
Initial audit base: main at 6f532d07e76f40fb449fb87204d61513ecf74d4a
Follow-up main commits: 885b85e0cdf54bd3cdf7367e05e700bbf8a06e60 (strict AI schema implementation), f041c558a2fe0a32b2ae6ec957d6e00358b67d30 (regression tests).
Purpose: Preserve the useful work and unresolved gaps from PRs #27–#37 before any branch deletion.

## Important limitation

This is a GitHub source/PR metadata audit. A full local clone, full test suite, and end-to-end runtime validation were not available in this audit environment. PR descriptions report their own tests, but those reports are not treated as proof that the current main tree passes all tests. Do not treat this document as a release sign-off.

## Live PR state

| PR | Current state | Work area | Audit decision |
|---|---|---|---|
| #27 | Closed, not merged | Windows job lock, OCR quality gate, acceptance/report artifacts | Most implementation is present in main; preserve unique report artifacts before deleting branch. |
| #28 | Open | Windows idempotency lock, OCR thresholds/tests, Wrangler previews | Overlaps main heavily. Do not merge blindly; verify threshold semantics and missing tests. |
| #29 | Merged | Retryable error taxonomy and exact D1 job/outbox state transitions | Merged; core code is present in main. |
| #30 | Merged | Circuit breaker single half-open probe and stale/cancelled completion handling | Merged; core code is present in main. |
| #31 | Open | Strict AI analysis output schema | The missing strict-key and finite-confidence checks have now been applied directly to main with regression tests; CI/test execution on the new commits is still pending. The remaining PR is no longer needed for those exact code changes, but check any branch-only differences before deleting. |
| #32 | Open, draft | Persisted user/purpose/document-scoped AI consent | Main contains consent-store and scoped-grant checks. Verify all provider entry points and regression tests before closing/deleting this branch. |
| #33 | Open | OCR benchmark report/quality-gate correction | Current report says gate is not ready and correctly marks Myanmar language sample missing, but it does not contain the proposed explicit quality_gate/per-sample failure-count evidence. Review and reconcile rather than overwrite. |
| #34 | Merged | Canonical cloud API origin in dashboard | Merged; PersonalDashboard.tsx imports CLOUD_API_ORIGIN. |
| #35 | Merged | Remove global 1px border regression | Merged; index.css preserves Tailwind's zero-width border reset. |
| #36 | Open | Workspace UI redesign plus API-origin/CSS fixes | API-origin and border portions overlap merged changes. Compare the remaining UI-only changes and run frontend build/tests before deciding what to apply. |
| #37 | Merged | Distinct Myanmar (mya) and English (eng) OCR benchmark requirements | Merged; retain the distinct-language benchmark gate. |

## Verified on current main

- web-platform/backend/app/services/job_idempotency.py contains POSIX fcntl and Windows msvcrt locking paths.
- web-platform/backend/app/services/ocr_benchmark.py contains CER/WER threshold checks and computes gate_ready.
- web-platform/tests/test_ocr_benchmark.py exists and checks a not-ready report case.
- cloudflare_worker/jobs.py contains JobStateConflict and guards expected row transitions.
- cloudflare_worker/outbox.py contains retryability classification and retry/dead transitions.
- web-platform/backend/app/services/train1_safety_contracts.py contains retry classification and the _probe_in_flight circuit-breaker guard.
- web-platform/backend/app/services/unified_ai_service.py imports the persisted consent store and validates scoped grants at external provider boundaries.
- Follow-up main commit 885b85e0cdf54bd3cdf7367e05e700bbf8a06e60 rejects unknown AI analysis keys and non-finite confidence values; commit f041c558a2fe0a32b2ae6ec957d6e00358b67d30 adds regression tests for unknown keys, NaN, and Infinity. These changes were source-verified but not yet fully test-run in this environment.
- wrangler.jsonc contains an empty previews block.
- web-platform/frontend/src/lib/cloudDocuments.ts exports CLOUD_API_ORIGIN; PersonalDashboard.tsx reuses it.
- web-platform/frontend/src/index.css no longer applies a global border-width: 1px.
- OCR report docs/Report/ocr-benchmark.json has gate_ready: false, lists required languages mya and eng, and says mya is missing because the existing Myanmar-related sample is mixed mya+eng.

## Outstanding implementation/verification checklist for main-only work

1. AI output schema (#31): implemented directly on main in commits 885b85e0cdf54bd3cdf7367e05e700bbf8a06e60 and f041c558a2fe0a32b2ae6ec957d6e00358b67d30. Verify the focused tests and confirm CI is green; preserve current required-field/type checks.
2. OCR benchmark evidence (#28/#33/#37): decide and document the authoritative CER/WER thresholds. The current service defaults observed on main are mean CER 0.30 and mean WER 0.60; PR #28 describes those values, while PR #33 describes a stricter quality gate of CER 0.10 and WER 0.20. Do not mix these contracts silently. Ensure the JSON report contains an explicit, reproducible quality-gate result and remains not-ready until a separate Myanmar sample exists and every required quality threshold passes.
3. Windows lock (#27/#28): keep current cross-platform lock implementation; verify Windows multiprocess behavior in a Windows CI/pilot environment. This was not proven by the current source audit.
4. Retry/DLQ (#29): merged code checks conditional state transitions; run targeted tests against current main and verify retry exhaustion / dead-letter behavior and retryable vs non-retryable status classification.
5. Circuit breaker (#30): merged code has a single in-flight half-open probe; run targeted tests for concurrent probes, stale completions, cancellation, and reopen behavior.
6. Consent boundary (#32): verify every external provider adapter, including OpenAI-compatible provider paths, goes through the same persisted consent guard; add/retain tests proving global consent alone or a forged in-memory grant cannot authorize disclosure.
7. Workspace redesign (#36): preserve merged API-origin and CSS fixes. Inspect the exact remaining UI diff before applying; keep routes, authentication/session behavior, cloud document lifecycle, and local/cloud boundaries. Run frontend build, tests, and lint, then browser preview acceptance for CORS/authenticated flows.
8. Wrangler preview: keep preview isolated from production D1/rate-limit bindings. The PR descriptions note a Python Worker preview command/configuration mismatch; verify the actual Cloudflare preview build command rather than assuming the empty previews block fixes it.
9. Full verification: run the focused tests above, then backend suite, frontend build/tests/lint, security/dependency checks, and CI on the final main commit. Record failures and environment blockers explicitly.

## Branch deletion guidance

- Already merged PR branches: #29, #30, #34, #35, #37. Their PR changes are in main; deleting those source branches is generally safe after confirming no external workflow depends on the branch names.
- Do not delete yet: #28, #32, #33, #36. They are open and have changes or validation evidence that must be reconciled with main first.
- #31's primary implementation is now on main; before deleting its branch, compare the exact branch-only diff and verify CI for the new main commits.
- #27 is closed without merge. Core Windows/OCR functionality is present in main, but first preserve/review its unique report artifacts and compare any remaining diff.
- Do not force-merge old branch heads: they diverge substantially from current main. Apply only confirmed missing changes to main and test them.

## Source links

- #27 https://github.com/logixaflow-commits/doka-ai-dms/pull/27
- #28 https://github.com/logixaflow-commits/doka-ai-dms/pull/28
- #29 https://github.com/logixaflow-commits/doka-ai-dms/pull/29
- #30 https://github.com/logixaflow-commits/doka-ai-dms/pull/30
- #31 https://github.com/logixaflow-commits/doka-ai-dms/pull/31
- #32 https://github.com/logixaflow-commits/doka-ai-dms/pull/32
- #33 https://github.com/logixaflow-commits/doka-ai-dms/pull/33
- #34 https://github.com/logixaflow-commits/doka-ai-dms/pull/34
- #35 https://github.com/logixaflow-commits/doka-ai-dms/pull/35
- #36 https://github.com/logixaflow-commits/doka-ai-dms/pull/36
- #37 https://github.com/logixaflow-commits/doka-ai-dms/pull/37


## Follow-up verification — 2026-10-13

- Current main head at this follow-up: `02b025c7497734d22ac2c1542a79aa3f4133543b` (`fix: declare Redis dependency for local backend`).
- GitHub Actions run [38369055323](https://github.com/logixaflow-commits/doka-ai-dms/actions/runs/38369055323) completed successfully for the cloud storage contract tests, repository self-audit preflight, workflow sanity, backend regression suite, static analysis/SBOM, backend dependency audit, symlink security tests, root dependency audit, and frontend build/smoke tests. The Vercel status returned success for this head. These results do not replace live provider acceptance.
- Branch inventory now returns only `main`, `fix/myanmar-ocr-text-preservation`, the backend Dependabot branch, and the frontend Dependabot branch. The older PR/branch table above is historical and must not be read as a current branch inventory.
- PR #23 (frontend dependency group) was closed on 2026-10-13 without merging. Its branch was 210 commits behind current main and changed package.json plus package-lock.json as a large batch; it should be regenerated against current main if updates are still needed.
- PR #47 (backend dependency group) remains open and is only one commit ahead of current main, but its six requirement files include major-version jumps (including filelock, OpenCV, pandas, NumPy, Pillow, cryptography, Redis and testing tools). Do not merge until the exact PR-head checks pass and the dependency resolution/build/test matrix is verified.
- `fix/myanmar-ocr-text-preservation` is 13 commits ahead and 47 behind main. It has a distinct regression workflow/test and OCR/Google Drive edits, but it is heavily diverged. Do not merge the whole branch; compare each remaining change with current main and cherry-pick/reimplement only a confirmed missing, tested fix.
- OCR acceptance remains NOT READY: the checked-in report's strict target is CER <= 10% and WER <= 20%; its latest acceptance rerun has six sample-threshold violations and `gate_ready: false`. Keep this gate closed until the sample/reference evidence is valid and the required language-specific samples pass.
- Still pending for release: authenticated B2 upload/download/checksum/delete/quota/recovery and >50 MiB boundary; real Google Drive OAuth/export/retrieval; Supabase two-user RLS acceptance; Cloudinary application-path validation; Windows multiprocess lock pilot; backup/restore; browser E2E and full UI acceptance. Do not mark these complete from source inspection or unauthenticated 401 probes.


### OCR regression follow-up — 2026-10-13

- Main now updates `OCRService._clean_text` to normalize Unicode to NFC, remove control artifacts while preserving newlines/tabs and Myanmar format characters, and retain valid one-character lines (including Myanmar numerals).
- Main now retries image OCR against an untouched copy of the original pixels when preprocessing produces no usable text. It does not retry when the preprocessed image already produces text.
- Regression tests were added for single-character line preservation, Unicode/control-artifact cleanup, raw-pixel retry, and the no-unnecessary-retry case. Commits: [implementation](https://github.com/logixaflow-commits/doka-ai-dms/commit/bbc38ba906253db0aefc17842949b6c408f7a9f6), [tests](https://github.com/logixaflow-commits/doka-ai-dms/commit/d019ca3a96df0e95dca3b3be89b8d1e6513b53fe), [source-pixel assertion](https://github.com/logixaflow-commits/doka-ai-dms/commit/e32f17161aa1ae57fed8826f9a7bf5124f0b87a5).
- The commits' combined status endpoint has not returned a GitHub Actions result yet; the only returned status before the latest test commit was Vercel success. Treat the new regression tests as **pending CI verification**, not as passed.
