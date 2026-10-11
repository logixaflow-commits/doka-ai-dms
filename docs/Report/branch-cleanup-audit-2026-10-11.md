# Branch Cleanup Audit — 2026-10-11

Repository: logixaflow-commits/doka-ai-dms
Audited base: main at 6f532d07e76f40fb449fb87204d61513ecf74d4a
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
| #31 | Open | Strict AI analysis output schema | A specific gap remains: current main checks required keys but does not reject extra keys; finite confidence validation also needs explicit verification. |
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
- wrangler.jsonc contains an empty previews block.
- web-platform/frontend/src/lib/cloudDocuments.ts exports CLOUD_API_ORIGIN; PersonalDashboard.tsx reuses it.
- web-platform/frontend/src/index.css no longer applies a global border-width: 1px.
- OCR report docs/Report/ocr-benchmark.json has gate_ready: false, lists required languages mya and eng, and says mya is missing because the existing Myanmar-related sample is mixed mya+eng.

## Outstanding implementation/verification checklist for main-only work

1. AI output schema (#31): update _parse_analysis_result to reject unknown keys, reject non-finite confidence values (NaN/Infinity), and add regression tests for both cases. Preserve current required-field/type checks.
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
- Do not delete yet: #28, #31, #32, #33, #36. They are open and have changes or validation evidence that must be reconciled with main first.
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
