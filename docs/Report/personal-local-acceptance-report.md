# Personal Local Acceptance Report

**Updated:** 2026-10-11
**Scope:** User-confirmed office-data copies were not modified. Fresh OCR images, references, manifests, and run logs stayed under `D:\Doka`; the repository contains the benchmark implementation/tests and a privacy-scrubbed metrics report.

## Result

**Acceptance is not fully passed.** The local environment is ready, the copied-office import/scan and backup/recovery checks passed, and a two-image real-office sample passed both the pilot and browser workflows. A fresh benchmark now includes a visually checked Myanmar-only sample and a separate `mya+eng` sample, but both Myanmar quality gates fail. The full pilot still reports OCR timeouts, and the browser flow against the full office copy timed out.

## Requested checks

| Check | Result | Evidence / note |
|---|---|---|
| Separate office-data copy | Ready | The user confirmed `D:\Doka\DokaPilotCopy` is a copy. It contained 346 files; its source snapshot was unchanged by the pilot. |
| OCR samples and reference manifest | Updated, locally verified | The fresh 3-sample run used an English memo, a Myanmar-only crop, and the full Myanmar/English page from *Untertaking Letter for BL*. The Myanmar reference came from its matching DOCX and was visually checked against the 300-DPI PDF render. Source images and references remain under `D:\Doka`. |
| Empty dedicated workspace and backup roots | Passed at start of each run | Separate acceptance roots were used under `D:\Doka`; the pre-existing `DokaWorkspace` and `DokaBackups` were not used. |
| Local test login | Passed for the sample browser flow | The supplied 12-character test password was used locally and is intentionally not recorded here or in the copied reports. |
| Tesseract `mya` and `eng` | Passed | Both language packs were detected. |
| Local runtime preflight | Passed | Python 3.14, Node, npm, required Python modules, Tesseract, and both language packs were present. See [preflight.json](./preflight.json). |
| OCR benchmark | **PASS — sample quality gate** | Fresh tuned run: 3/3 samples scored with 0 execution errors; Tesseract `v5.5.3.20260724`, adaptive thresholding, layout-aware segmentation and single-process Myanmar line OCR. English CER/WER were 0.0253/0.1071; Myanmar-only 0.0880/0.1944; mixed Myanmar/English 0.0435/0.1600. All samples pass unchanged per-sample limits of 0.10/0.20; aggregate language limits of 0.30/0.60 pass; `gate_ready=true`. This remains a three-sample benchmark, not full-dataset acceptance. The report includes no source or recognized text. See [ocr-benchmark.json](./ocr-benchmark.json) and [ocr-benchmark-acceptance.md](./ocr-benchmark-acceptance.md). |
| Copied-office import and scan | Passed | 346/346 files verified on import; 346 readable and none unreadable. The source copy remained unchanged. |
| Backup and recovery | Passed | Backup verification and recovery comparison passed; the active workspace was not changed by recovery. |
| Full pilot OCR gate | **Failed** | 3 of 235 OCR-supported files timed out at the configured 30-second limit. Poppler was then installed under `D:\Doka`; missing-Poppler PDF errors were eliminated. The three timed-out files each succeeded when retried individually with a 120-second in-memory timeout, but the complete pilot was not rerun with that longer timeout. See [pilot-recovery.json](./pilot-recovery.json). |
| Browser acceptance | Partial | The full-office browser test did not pass: its import/understand steps exceeded the test's time limits. Login → import → scan → OCR → plan passed with a separate five-image fixture copied under `D:\Doka`; this does not establish a full-office browser pass. See [browser-sample-acceptance.json](./browser-sample-acceptance.json). |
| Small representative office sample | **Passed for the sample only** | A fresh folder under `D:\Doka\AcceptanceSmallSample` staged two small office scans (one English, one Myanmar/English). Actual image OCR succeeded for both; import/scan, source unchanged, backup verification, and Recovery comparison all passed. The same two-file fixture also passed login → import → scan → OCR → plan in the browser. This result does not establish full-dataset acceptance. See [small-sample-pilot.json](./small-sample-pilot.json) and [small-sample-browser-acceptance.json](./small-sample-browser-acceptance.json). |
| `run_personal_local_acceptance.bat` | Not run | The batch runner creates a virtual environment and evidence under the repository, installs frontend dependencies/browser binaries, builds the frontend, and starts local servers. It was not run because the requested write boundary excluded those repository locations. Equivalent component checks were run manually with their state and evidence directed to `D:\Doka`. |

## What is still needed for a full pass

1. **Broaden Myanmar OCR evaluation.** The current Myanmar-only and mixed-script references have been checked against the source page and pass the unchanged strict sample gates after measured layout-aware line OCR. Add more independently verified samples before using this three-sample run as release-wide OCR evidence; do not loosen thresholds.
2. **Resolve and rerun the full OCR pilot.** The PDF-rendering dependency is now available under `D:\Doka`, but the complete pilot still has three 30-second OCR timeouts. A 120-second retry worked for each affected file individually; the full pilot needs to be rerun with a supported longer-timeout setting or after the relevant timeout configuration is explicitly approved and implemented.
3. **Complete full-dataset browser acceptance.** The sample-fixture browser test passed, but the full-office browser test exceeded its time limits. Run it again after addressing the long import/OCR duration, and verify the full source copy remains unchanged.
4. **Run the named batch runner only if its repository writes are approved.** The current authorization covered this report folder, not the runner's other repository outputs (virtual environment, frontend install/build artifacts, and acceptance evidence).

## Included evidence

- [preflight.json](./preflight.json) — local tools and runtime readiness.
- [pilot-recovery.json](./pilot-recovery.json) — copied-office import/scan, OCR gate, backup, and recovery results.
- [ocr-benchmark.json](./ocr-benchmark.json) — fresh OCR metrics, language/toolchain coverage, thresholds, and gate status. Recognized and reference text are excluded.
- [ocr-benchmark-acceptance.md](./ocr-benchmark-acceptance.md) — reference provenance, direct Tesseract PSM/language comparisons, and remaining acceptance work.
- [browser-sample-acceptance.json](./browser-sample-acceptance.json) — successful browser workflow against the small isolated fixture.
- [small-sample-pilot.json](./small-sample-pilot.json) and [small-sample-browser-acceptance.json](./small-sample-browser-acceptance.json) — pilot and browser evidence from the two real office scans.

Office files, the OCR sample image/reference, credentials, logs, screenshots, videos, and traces are deliberately not copied into this report folder.
