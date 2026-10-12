# Personal Local Full-Copy Acceptance Report

**Updated:** 2026-10-12
**Source:** User-provided copy at `D:\Doka\DokaPilotCopy`
**Scope:** Full copied-office import, scan, OCR, plan generation, browser workflow, source immutability, backup and isolated recovery.

Machine-readable, privacy-safe summary: [personal-local-acceptance.json](./personal-local-acceptance.json).

## Overall result

**Release gates remain open.** The latest copied-office validation run on 2026-10-12, against HEAD `772a05ac539355b58494e5b10f6c75e94cd1cab4` plus uncommitted local import and OCR fixes, imported and scanned all 346 files, produced non-empty OCR for all 235 supported files, and verified backup and isolated recovery. A Chromium run on the same HEAD plus local patch also passed login (including invalid-password rejection), copy import, scan, OCR/understanding, plan generation, and authenticated reload against the same representative copy. Source snapshots were unchanged. The run used PDFium because Poppler's `pdfinfo` executable is unavailable. These tests pass the copy/import/OCR/recovery and browser paths, but do **not** complete full Gate 5: a human still needs to review/approve and apply a final copy. The expanded OCR accuracy benchmark still fails its unchanged thresholds.

The current-run machine-readable summary is [personal-local-current-run.json](./personal-local-current-run.json). It records the exact HEAD, local code-patch fingerprint, and browser/pilot results; the working tree was not clean, so this is not evidence for a clean committed release candidate or current-HEAD CI.

The separate expanded OCR quality gate remains **FAIL** at unchanged CER/WER thresholds. Three of five required samples fail the strict per-sample limits, and the mixed-script aggregate CER is above its unchanged limit. The exact benchmark CLI was rerun against the current candidate on 2026-10-12 and returned its documented failure exit code `2`: 5/5 samples scored, 0 execution errors, and the same six strict-threshold violations. Other `D:\Doka` manifests were scored separately: four of six `DokaOcrSamples` samples fail strict limits, while all three exploratory `OcrBenchmarkRun` samples are below per-sample limits but have not had their references adjudicated. Those additional runs include duplicated images and are not acceptance evidence. One required Myanmar-only reference was matched line by line against its DOCX; two additional source references remain provisional because discrepancies are unresolved. Therefore, do not describe all OCR quality or release gates as passed.

### Latest local run details

- Python 3.12.13; Tesseract 5.5.3.20260724 with `eng`, `mya`, and `osd`; OCR timeout set to 120 seconds. AI and external-processing consent were false; original-read-only was true and source writes were disabled.
- The first pilot attempt exposed a Windows bug: the import tried to call `os.chmod` with an integer file descriptor. The fix now uses `os.fchmod` on POSIX and the destination path on Windows, while retaining handle-based timestamp updates on Windows. The stricter import regression test now requires every fixture file to verify.
- The latest rerun found `pdfinfo` unavailable; 16 scanned PDFs therefore failed through the Poppler renderer. OCR now falls back to PDFium only for that missing-tool error, preserving Poppler's existing path when available and capping PDFium renders at 3500 px on the longest edge.
- With the fallback, 346/346 source files imported and verified, 346/346 scanned as readable, and the source copy remained unchanged. All 235 supported OCR results were non-empty, and the copy/import/OCR/recovery pilot script passed.
- The backup archive verified, isolated recovery matched the pre-backup workspace, and recovery did not modify the active workspace. This proves the technical drill, not owner acceptance of an RTO/RPO target.
- Focused OCR, benchmark, import-safety, and containment tests: 23 passed, 3 skipped. The separate OCR accuracy benchmark still fails at its unchanged thresholds.

## Results

| Check | Result | Evidence |
|---|---|---|
| Latest copied-office validation (2026-10-12) | **Technical checks PASS; full Gate 5 pending** | On HEAD `772a05ac539355b58494e5b10f6c75e94cd1cab4` plus the local import/OCR patch, 346/346 files imported and SHA-256 verified; 346/346 scanned readable; AI remained disabled; all 235 supported OCR results were non-empty; source copy unchanged. Human review, approval, and final-copy/apply remain untested. |
| Latest backup and isolated recovery drill | **Technical drill PASS; Gate 6 pending target sign-off** | Backup verified, isolated recovery matched, and active workspace was unchanged. Backup create: 62.031 s; verify: 3.375 s; restore: 37.266 s. Owner-approved RTO/RPO targets have not been supplied, so Gate 6 is not claimed complete. |
| Latest OCR execution on copied office data | **PASS** | 235/235 supported files returned non-empty results with `eng`, `mya`, and `mya+eng` detected. PDFium fallback was used because Poppler was unavailable; longest rendered edge is capped at 3500 px. |
| Latest representative-copy browser E2E (2026-10-12) | **PASS; full Gate 4 partial** | Chromium passed wrong-password rejection, valid login, import, scan, OCR/understanding (235 supported; 0 empty), 346-proposal review-plan generation, and authenticated page reload. Its before/after source-hash comparison passed; the post-run aggregate tree SHA-256 was `2e8fa189902f8ef898744eb205f075e867dc1f6c2a0566f1a8fbf4e232ed9bd8`. The test does not simulate a service restart or final-copy approval/apply. It ran at HEAD `772a05ac539355b58494e5b10f6c75e94cd1cab4` plus the patch fingerprint in the current-run JSON. |
| Current expanded OCR accuracy benchmark | **FAIL** | Exact repository CLI rerun scored the same verified 5-sample set with zero execution errors and exited `2`, the documented quality-failure exit. Three samples still fail unchanged strict CER/WER limits; `mya+eng` mean CER remains 0.3379 against 0.30. |
| Additional `D:\Doka` OCR sample manifests | **Exploratory; not acceptance evidence** | `DokaOcrSamples`: 6/6 scored, 4 strict failures. One mixed-script sample's 10 reference lines match one unique PDF source in the copied-office corpus; its 418-variant sweep improved the score from 0.4706/1.2619 to a best 0.1634/0.3333, still failing both strict limits. The other five references remain unverified; no settings were adopted. `OcrBenchmarkRun`: 3/3 scored, no strict failures, but reference provenance remains unadjudicated. Hash comparison found duplicates across manifests; five browser sample images duplicate the six-sample set and have no verified reference manifest. Full separate metrics and caveats are in [ocr-benchmark-acceptance.md](./ocr-benchmark-acceptance.md). |
| Source-copy integrity | **PASS** | The supplied copy contained 346 files. Both the latest pilot and latest browser test reported matching source snapshots. The latest browser-run aggregate tree digest was `2e8fa189902f8ef898744eb205f075e867dc1f6c2a0566f1a8fbf4e232ed9bd8`. |
| Full copied-office import | **PASS** | 346/346 files verified; 0 import failures. |
| Full copied-office scan | **PASS** | 346/346 files readable; 0 unreadable. |
| Earlier full-copy OCR execution | **PASS (historical run)** | The earlier 235-file run had 0 empty/failed results and no timeout messages. This is retained as historical evidence; the latest run is recorded above. |
| OCR recovery and rendering | **PASS (technical)** | A page that remains empty after preprocessing is retried once against the original render. When Poppler is unavailable, PDFium renders the PDF instead; the latest pilot returned non-empty output for all 235 supported files. |
| Organization plan | **Generated; approval required** | 346 proposals were produced. The pilot did not apply proposals; user approval remains required. |
| Earlier backup and isolated recovery | **PASS (historical run)** | The earlier recovery comparison passed in 14.722 seconds without changing the active workspace. Latest timing is listed above. |
| Earlier full-copy browser acceptance | **PASS (historical run)** | Chromium 1.64.0 ran login → import → scan → understand/OCR → plan against commit `49d27378c4055e5846254cf719fd2297bf86a3ff`; the worktree was clean at run start. 1/1 test passed in 948,889 ms (about 15.8 minutes). Import and analysis covered all 346 files; all 235 supported OCR results were non-empty. Aggregate source-tree SHA-256 before and after was identical. |
| Expanded OCR quality benchmark | **FAIL** | 5/5 samples scored with 0 execution errors across 4 distinct documents and 3 Myanmar-containing documents. The unchanged strict sample gate fails for 3 samples. Mixed-script mean CER is 0.3379 against a 0.30 aggregate limit. |
| Myanmar reference verification | **PARTIAL** | All 7 non-empty lines of the Myanmar-only reference match its source DOCX. The Plavix and cool-storage references were checked against their best-matching paired searchable PDFs, 300-DPI PDFium renders and DOCX text, but 11/23 and 5/16 lines respectively remain below 95% source-text alignment. Do not treat those two scores as fully verified ground-truth accuracy. |
| Rendering-font evidence | **PARTIAL** | The two newly added reference-page images were rendered with PDFium without missing-display-font diagnostics. The successful full-pilot log contained 0 Poppler font-warning messages. Poppler fallback fonts themselves were not replaced; this does not prove every PDF-rendering path is warning-free. |
| Targeted tests and lint | **PASS** | Focused OCR, benchmark, import-safety, and containment tests: 23 passed, 3 skipped. The changed Playwright test passed targeted ESLint and the full Chromium E2E. The frontend build had passed in the earlier local run; no new build was needed for this test-only frontend edit. |
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

The latest copied-office run used Tesseract `v5.5.3.20260724`, with `eng` and `mya` language data, at a 120-second OCR timeout. Adaptive preprocessing remains enabled by default. When it produces no normalized text from a PDF page, OCR retries that page once without preprocessing. Since `pdfinfo` was unavailable, the run used the new PDFium fallback for scanned PDFs; it completed in 635.485 seconds, returned non-empty output for all 235 supported files, and left the source copy unchanged.

The historical report about two PDFs with empty text describes an earlier run, not this final pilot. The latest `understanding.json` contains 211/211 PDFs with non-empty results, the full pilot reports 0/235 OCR failures, and its log records four preprocessing-empty pages successfully recovered by the raw-image retry. Thus the older two-empty-PDF observation is superseded; it is not an unresolved failure in the latest run.

## Private evidence

- Full pilot metrics: `D:\Doka\PFR9f60\E\pilot.json`
- Current-HEAD browser integrity summary: `D:\Doka\BA20261012b\E\browser-source-integrity.json`
- Current-HEAD Playwright JSON and full logs: `D:\Doka\BA20261012b\E`
- Expanded OCR benchmark private manifest/images: `D:\Doka\MyanmarBenchmarkExpanded`
- Reference verification and controlled OCR metrics: `D:\Doka\MyanmarBenchmarkExpanded\reference-review`
- Privacy-scrubbed OCR metrics: [ocr-benchmark.json](./ocr-benchmark.json)
- Latest copied-office/OCR/recovery metrics: [personal-local-current-run.json](./personal-local-current-run.json)
- Ground-truth notes and rerun command: [ocr-benchmark-acceptance.md](./ocr-benchmark-acceptance.md)

Source office files, reference/OCR text, credentials, full logs, and browser artifacts remain under `D:\Doka`. No such contents were copied into repository reports.

## Remaining work

1. Resolve the 11 Plavix and 5 cool-storage reference lines below 95% source alignment; mark illegible glyphs unresolved rather than guessing.
2. Improve OCR quality on the three strict-gate failures without changing CER/WER thresholds; the current benchmark remains **FAIL**.
3. Complete full Gate 5 review, explicit human approval, and final-copy/apply on a privacy-approved copy; the latest pilot generated a plan but did not apply it.
4. Test an actual service restart in the browser acceptance environment; the current run verified authenticated page reload, not restarting backend/frontend processes. Rerun the complete browser flow on a committed final candidate and record its exact SHA.
5. Agree explicit owner-approved RTO/RPO targets before marking Gate 6 complete.
6. Run exact-HEAD GitHub Actions through the repository's normal commit/PR workflow before claiming CI status. No commit or push has been performed.
