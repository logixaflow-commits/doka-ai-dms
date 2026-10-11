# Personal Local Full-Copy Acceptance Report

**Updated:** 2026-10-12
**Source:** User-provided copy at `D:\Doka\DokaPilotCopy`
**Scope:** Full copied-office import, scan, OCR, plan generation, browser workflow, source immutability, backup and isolated recovery.

Machine-readable, privacy-safe summary: [personal-local-acceptance.json](./personal-local-acceptance.json).

## Overall result

**The full-copy pilot and requested browser workflow passed. The OCR accuracy benchmark did not pass.** All 346 copied files imported and scanned; all 235 supported OCR files returned non-empty text, including Myanmar and English coverage. The full Playwright flow passed and confirmed the source copy's SHA-256 snapshot was identical before and after. Backup verification and isolated recovery passed.

The separate expanded OCR quality gate remains **FAIL** at unchanged CER/WER thresholds. Three of five samples fail the strict per-sample limits, and the mixed-script aggregate CER is above its unchanged limit. Two of the three Myanmar-bearing document references still need complete manual line-by-line verification. Therefore, do not describe all OCR quality or release gates as passed.

## Results

| Check | Result | Evidence |
|---|---|---|
| Source-copy integrity | **PASS** | The supplied copy contained 346 files. Full-pilot before/after hashes matched; the browser test also compared every file's SHA-256 before and after the workflow and passed. |
| Full copied-office import | **PASS** | 346/346 files verified; 0 import failures. |
| Full copied-office scan | **PASS** | 346/346 files readable; 0 unreadable. |
| Full copied-office OCR execution | **PASS** | 235 supported files; 0 empty/failed results; 0 timeout messages; language coverage included `eng`, `mya`, and `mya+eng`. The 120-second timeout remained bounded by runtime configuration. |
| OCR empty-page recovery | **PASS** | The service retries a PDF page once against the original render only if adaptive preprocessing produces no normalized text. The full pilot used this fallback four times; it recovered non-empty output without changing source files. |
| Organization plan | **Generated; approval required** | 346 proposals were produced. The pilot did not apply proposals; user approval remains required. |
| Backup and isolated recovery | **PASS** | Backup verification and recovery comparison passed. Restore took 14.722 seconds, and recovery did not change the active workspace. |
| Full-copy browser acceptance | **PASS** | Chromium ran login → import → scan → understand/OCR → plan. Import and analysis each covered all 346 files; all 235 supported OCR results were non-empty. The test passed in 815,401 ms (about 13.6 minutes). |
| Expanded OCR quality benchmark | **FAIL** | 5/5 samples scored with 0 execution errors across 4 distinct documents and 3 Myanmar-containing documents. The unchanged strict sample gate fails for 3 samples. Mixed-script mean CER is 0.3379 against a 0.30 aggregate limit. |
| Myanmar reference verification | **PARTIAL** | One Myanmar-bearing source has a visually checked reference. Two added PDF/DOCX-derived references were compared with rendered pages but still require full manual line-by-line validation; treat their metrics as provisional. |
| Rendering-font evidence | **PARTIAL** | The two newly added reference-page images were rendered with PDFium without missing-display-font diagnostics. The successful full-pilot log contained 0 Poppler font-warning messages. Poppler fallback fonts themselves were not replaced; this does not prove every PDF-rendering path is warning-free. |
| Targeted tests and build | **PASS** | OCR benchmark/input/line-safety/timeout/fallback tests: 23 passed, 3 skipped. Frontend TypeScript/Vite build, targeted Playwright lint, and Playwright test discovery passed. |
| GitHub Actions / publish | **NOT RUN** | No current-HEAD GitHub Actions run, commit, or push was performed. These local results must not be represented as CI evidence. |

## OCR benchmark detail

The thresholds were not reduced. The strict per-sample limits remain CER `0.10` and WER `0.20`; aggregate language limits remain CER `0.30` and WER `0.60`.

| Language | Samples | Mean CER | Mean WER | Strict per-sample result |
|---|---:|---:|---:|---|
| `eng` | 1 | 0.0253 | 0.1071 | Pass |
| `mya` | 1 | 0.1200 | 0.3056 | Fail |
| `mya+eng` | 3 | 0.3379 | 0.5342 | Fail; two samples exceed strict limits |

The mixed-script mean CER exceeds its aggregate limit; its mean WER remains below `0.60`. The machine-readable report anonymizes sample labels and includes aggregate/error counts only. It includes neither source/reference text nor recognized OCR text.

## Rendering and OCR handling

The two new Myanmar-containing source-page images were rendered at 300 DPI with PDFium to avoid the missing-display-font diagnostics previously seen with Poppler on those pages. This is a renderer choice for the staged benchmark images, not a repair to Poppler's installed fallback-font set.

The full pilot used Tesseract `v5.5.3.20260724`, with `eng` and `mya` language data, at a 120-second per-operation timeout. Adaptive preprocessing remains enabled by default. When it produces no normalized text from a PDF page, OCR retries that page once without preprocessing. The full pilot completed in 608.695 seconds and logged no OCR timeouts or Poppler font warnings.

## Private evidence

- Full pilot metrics: `D:\Doka\PFR9f60\E\pilot.json`
- Full browser Playwright JSON: `D:\Doka\BR70fb7\E\playwright-full.json`
- Expanded OCR benchmark private manifest/images: `D:\Doka\MyanmarBenchmarkExpanded`
- Privacy-scrubbed OCR metrics: [ocr-benchmark.json](./ocr-benchmark.json)
- Ground-truth notes and rerun command: [ocr-benchmark-acceptance.md](./ocr-benchmark-acceptance.md)

Source office files, reference/OCR text, credentials, full logs, and browser artifacts remain under `D:\Doka`. No such contents were copied into repository reports.

## Remaining work

1. Manually verify both added Myanmar references line by line against their source pages; record uncertain characters rather than guessing.
2. Improve OCR quality on the three strict-gate failures without changing the CER/WER thresholds; rerun and report the measured results.
3. If the wider browser acceptance must include approving/copying proposals, browser backup/restore and undo, extend and run those actions separately. This browser test intentionally stopped at plan review; the full pilot verified backup and isolated recovery independently.
4. Run current-HEAD GitHub Actions through the repository's normal commit/PR workflow before claiming CI status.
