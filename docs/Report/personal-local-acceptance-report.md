# Personal Local Full-Copy Acceptance Report

**Updated:** 2026-10-12
**Source:** User-provided copy at `D:\Doka\DokaPilotCopy`
**Scope:** Full copied-office import, scan, OCR, plan generation, browser workflow, source immutability, backup and isolated recovery.

Machine-readable, privacy-safe summary: [personal-local-acceptance.json](./personal-local-acceptance.json).

## Overall result

**The full-copy pilot and full browser workflow passed on the recorded source copy. The OCR accuracy benchmark did not pass.** All 346 copied files imported and scanned; all 235 supported OCR files returned non-empty text, including Myanmar and English coverage. A Chromium run against commit `49d27378c4055e5846254cf719fd2297bf86a3ff` passed the full Playwright flow and recorded identical aggregate source-tree SHA-256 digests before and after the run. Backup verification and isolated recovery passed.

The separate expanded OCR quality gate remains **FAIL** at unchanged CER/WER thresholds. Three of five samples fail the strict per-sample limits, and the mixed-script aggregate CER is above its unchanged limit. One Myanmar-only reference was matched line by line against its DOCX; two additional source references remain provisional because discrepancies are unresolved. Therefore, do not describe all OCR quality or release gates as passed.

## Results

| Check | Result | Evidence |
|---|---|---|
| Source-copy integrity | **PASS** | The supplied copy contained 346 files. The pilot reported the source unchanged. The current-HEAD browser harness computed per-file hashes before and after all browser steps; the deterministic aggregate tree digest matched (`54cea99339b574293646808537ebd6d9ab186994a62d540b07a0d2ad23cab2bb`). |
| Full copied-office import | **PASS** | 346/346 files verified; 0 import failures. |
| Full copied-office scan | **PASS** | 346/346 files readable; 0 unreadable. |
| Full copied-office OCR execution | **PASS** | 235 supported files; 0 empty/failed results; 0 timeout messages; language coverage included `eng`, `mya`, and `mya+eng`. The 120-second timeout remained bounded by runtime configuration. |
| OCR empty-page recovery | **PASS** | The service retries a PDF page once against the original render only if adaptive preprocessing produces no normalized text. The full pilot used this fallback four times; it recovered non-empty output without changing source files. |
| Organization plan | **Generated; approval required** | 346 proposals were produced. The pilot did not apply proposals; user approval remains required. |
| Backup and isolated recovery | **PASS** | Backup verification and recovery comparison passed. Restore took 14.722 seconds, and recovery did not change the active workspace. |
| Full-copy browser acceptance | **PASS** | Chromium 1.64.0 ran login → import → scan → understand/OCR → plan against commit `49d27378c4055e5846254cf719fd2297bf86a3ff`; the worktree was clean at run start. 1/1 test passed in 948,889 ms (about 15.8 minutes). Import and analysis covered all 346 files; all 235 supported OCR results were non-empty. Aggregate source-tree SHA-256 before and after was identical. |
| Expanded OCR quality benchmark | **FAIL** | 5/5 samples scored with 0 execution errors across 4 distinct documents and 3 Myanmar-containing documents. The unchanged strict sample gate fails for 3 samples. Mixed-script mean CER is 0.3379 against a 0.30 aggregate limit. |
| Myanmar reference verification | **PARTIAL** | All 7 non-empty lines of the Myanmar-only reference match its source DOCX. The Plavix and cool-storage references were checked against their best-matching paired searchable PDFs, 300-DPI PDFium renders and DOCX text, but 11/23 and 5/16 lines respectively remain below 95% source-text alignment. Do not treat those two scores as fully verified ground-truth accuracy. |
| Rendering-font evidence | **PARTIAL** | The two newly added reference-page images were rendered with PDFium without missing-display-font diagnostics. The successful full-pilot log contained 0 Poppler font-warning messages. Poppler fallback fonts themselves were not replaced; this does not prove every PDF-rendering path is warning-free. |
| Targeted tests and build | **PASS** | Latest focused OCR benchmark tests: 11 passed, 1 skipped. The expanded OCR input/line-safety/timeout/fallback selection previously passed 23 tests, 3 skipped. Frontend TypeScript/Vite build, targeted Playwright lint, and Playwright test discovery passed. |
| GitHub Actions / publish | **NOT RUN** | No current-HEAD GitHub Actions run, commit, or push was performed. These local results must not be represented as CI evidence. |

## OCR benchmark detail

The thresholds were not reduced. The strict per-sample limits remain CER `0.10` and WER `0.20`; aggregate language limits remain CER `0.30` and WER `0.60`.

| Language | Samples | Mean CER | Mean WER | Strict per-sample result |
|---|---:|---:|---:|---|
| `eng` | 1 | 0.0253 | 0.1071 | Pass |
| `mya` | 1 | 0.1200 | 0.3056 | Fail |
| `mya+eng` | 3 | 0.3379 | 0.5342 | Fail; two samples exceed strict limits |

The mixed-script mean CER exceeds its aggregate limit; its mean WER remains below `0.60`. The machine-readable report uses benchmark sample labels and includes aggregate/error counts only. It includes neither source/reference text nor recognized OCR text.

Controlled experiments tested language, preprocessing, rotation, cropping, row segmentation, Tesseract PSM, thresholding, scaling, per-row confidence selection, and the official Tesseract `tessdata_best` Myanmar model on the benchmark samples. No candidate made the failing mixed-script samples pass, and the Myanmar-only sample still misses both strict limits. No experimental OCR setting or model was applied to production. The model comparison and metrics are documented in [ocr-benchmark-acceptance.md](./ocr-benchmark-acceptance.md).

## Rendering and OCR handling

The two new Myanmar-containing source-page images were rendered at 300 DPI with PDFium to avoid the missing-display-font diagnostics previously seen with Poppler on those pages. This is a renderer choice for the staged benchmark images, not a repair to Poppler's installed fallback-font set.

The full pilot used Tesseract `v5.5.3.20260724`, with `eng` and `mya` language data, at a 120-second per-operation timeout. Adaptive preprocessing remains enabled by default. When it produces no normalized text from a PDF page, OCR retries that page once without preprocessing. The full pilot completed in 608.695 seconds and logged no OCR timeouts or Poppler font warnings.

The historical report about two PDFs with empty text describes an earlier run, not this final pilot. The latest `understanding.json` contains 211/211 PDFs with non-empty results, the full pilot reports 0/235 OCR failures, and its log records four preprocessing-empty pages successfully recovered by the raw-image retry. Thus the older two-empty-PDF observation is superseded; it is not an unresolved failure in the latest run.

## Private evidence

- Full pilot metrics: `D:\Doka\PFR9f60\E\pilot.json`
- Current-HEAD browser integrity summary: `D:\Doka\BA20261012b\E\browser-source-integrity.json`
- Current-HEAD Playwright JSON and full logs: `D:\Doka\BA20261012b\E`
- Expanded OCR benchmark private manifest/images: `D:\Doka\MyanmarBenchmarkExpanded`
- Reference verification and controlled OCR metrics: `D:\Doka\MyanmarBenchmarkExpanded\reference-review`
- Privacy-scrubbed OCR metrics: [ocr-benchmark.json](./ocr-benchmark.json)
- Ground-truth notes and rerun command: [ocr-benchmark-acceptance.md](./ocr-benchmark-acceptance.md)

Source office files, reference/OCR text, credentials, full logs, and browser artifacts remain under `D:\Doka`. No such contents were copied into repository reports.

## Remaining work

1. Resolve the 11 Plavix and 5 cool-storage reference lines below 95% source alignment; mark illegible glyphs unresolved rather than guessing.
2. Improve OCR quality on the three strict-gate failures without changing the CER/WER thresholds; rerun and report the measured results.
3. If the wider browser acceptance must include approving/copying proposals, browser backup/restore and undo, extend and run those actions separately. This browser test intentionally stopped at plan review; the full pilot verified backup and isolated recovery independently.
4. Run current-HEAD GitHub Actions through the repository's normal commit/PR workflow before claiming CI status. No commit, push, or current-HEAD CI run has been performed.
