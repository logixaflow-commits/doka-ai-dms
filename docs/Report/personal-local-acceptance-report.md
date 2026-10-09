# Personal Local Acceptance Report

**Date:** 2026-10-09  
**Scope:** Read-only use of the user-confirmed office-data copy; generated workspaces, backups, OCR samples, and test evidence stayed under `D:\Doka`. The repository change for this handoff is limited to this report and the four selected JSON reports in this folder.

## Result

**Acceptance is not fully passed.** The local environment is ready, the copied-office import/scan and backup/recovery checks passed, and the browser workflow passed against a small isolated fixture. The full pilot still reports OCR timeouts, the benchmark's Myanmar accuracy is poor and its reference has not been visually verified, and the browser flow against the full office copy timed out.

## Requested checks

| Check | Result | Evidence / note |
|---|---|---|
| Separate office-data copy | Ready | The user confirmed `D:\Doka\DokaPilotCopy` is a copy. It contained 346 files; its source snapshot was unchanged by the pilot. |
| OCR samples and reference manifest | Present, needs review | Five English samples and one Myanmar/English sample were benchmarked. The Myanmar reference was extracted from a text layer in the copied office PDF; a person has not checked it against the rendered scan. |
| Empty dedicated workspace and backup roots | Passed at start of each run | Separate acceptance roots were used under `D:\Doka`; the pre-existing `DokaWorkspace` and `DokaBackups` were not used. |
| Local test login | Passed for the sample browser flow | The supplied 12-character test password was used locally and is intentionally not recorded here or in the copied reports. |
| Tesseract `mya` and `eng` | Passed | Both language packs were detected. |
| Local runtime preflight | Passed | Python 3.14, Node, npm, required Python modules, Tesseract, and both language packs were present. See [preflight.json](./preflight.json). |
| OCR benchmark | Ran; accuracy needs work | 6/6 samples scored with no execution errors, but the Myanmar/English sample scored CER 79.94% and WER 171.43%. The benchmark's `gate_ready` indicates sample/language/tool availability, not acceptable OCR accuracy. See [ocr-benchmark.json](./ocr-benchmark.json). |
| Copied-office import and scan | Passed | 346/346 files verified on import; 346 readable and none unreadable. The source copy remained unchanged. |
| Backup and recovery | Passed | Backup verification and recovery comparison passed; the active workspace was not changed by recovery. |
| Full pilot OCR gate | **Failed** | 3 of 235 OCR-supported files timed out at the configured 30-second limit. Poppler was then installed under `D:\Doka`; missing-Poppler PDF errors were eliminated. The three timed-out files each succeeded when retried individually with a 120-second in-memory timeout, but the complete pilot was not rerun with that longer timeout. See [pilot-recovery.json](./pilot-recovery.json). |
| Browser acceptance | Partial | The full-office browser test did not pass: its import/understand steps exceeded the test's time limits. Login → import → scan → OCR → plan passed with a separate five-image fixture copied under `D:\Doka`; this does not establish a full-office browser pass. See [browser-sample-acceptance.json](./browser-sample-acceptance.json). |
| `run_personal_local_acceptance.bat` | Not run | The batch runner creates a virtual environment and evidence under the repository, installs frontend dependencies/browser binaries, builds the frontend, and starts local servers. It was not run because the requested write boundary excluded those repository locations. Equivalent component checks were run manually with their state and evidence directed to `D:\Doka`. |

## What is still needed for a full pass

1. **Validate Myanmar benchmark truth and quality.** Check the Myanmar reference against the rendered sample locally. If it does not match exactly, correct it; ideally add clear representative Myanmar and English samples with verified references. Agree on an acceptable CER/WER threshold—the runner does not currently make `gate_ready` an accuracy-threshold pass.
2. **Resolve and rerun the full OCR pilot.** The PDF-rendering dependency is now available under `D:\Doka`, but the complete pilot still has three 30-second OCR timeouts. A 120-second retry worked for each affected file individually; the full pilot needs to be rerun with a supported longer-timeout setting or after the relevant timeout configuration is explicitly approved and implemented.
3. **Complete full-dataset browser acceptance.** The sample-fixture browser test passed, but the full-office browser test exceeded its time limits. Run it again after addressing the long import/OCR duration, and verify the full source copy remains unchanged.
4. **Run the named batch runner only if its repository writes are approved.** The current authorization covered this report folder, not the runner's other repository outputs (virtual environment, frontend install/build artifacts, and acceptance evidence).

## Included evidence

- [preflight.json](./preflight.json) — local tools and runtime readiness.
- [pilot-recovery.json](./pilot-recovery.json) — copied-office import/scan, OCR gate, backup, and recovery results.
- [ocr-benchmark.json](./ocr-benchmark.json) — aggregate bilingual OCR benchmark results. Recognized and reference text are excluded.
- [browser-sample-acceptance.json](./browser-sample-acceptance.json) — successful browser workflow against the small isolated fixture.

Office files, the OCR sample image/reference, credentials, logs, screenshots, videos, and traces are deliberately not copied into this report folder.
