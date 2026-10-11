# OCR benchmark acceptance — expanded Myanmar sample set

**Updated:** 2026-10-12

## Result

**FAIL — the strict OCR quality gate does not pass.** The expanded run scored all five samples without execution errors, but the unchanged per-sample limits (`CER ≤ 0.10`, `WER ≤ 0.20`) fail for three samples. The mixed Myanmar/English aggregate CER also exceeds its unchanged limit of `0.30`. No score threshold was relaxed.

| Sample language | Samples | Mean CER | Mean WER | Strict per-sample gate |
|---|---:|---:|---:|---|
| `eng` | 1 | 0.0253 | 0.1071 | Pass |
| `mya` | 1 | 0.1200 | 0.3056 | Fail |
| `mya+eng` | 3 | 0.3379 | 0.5342 | Fail: two of three samples |

The `mya+eng` mean CER exceeds the unchanged aggregate limit of `0.30`; its mean WER remains under `0.60`. There were 0 benchmark execution errors, 5/5 scored samples, 4 distinct source documents, and 3 Myanmar-containing source documents. `gate_ready` is `false`. These are sample-set metrics, not a claim of release-wide accuracy.

## Ground truth, independence, and limits

- The benchmark now covers three distinct Myanmar-containing source documents, including a Myanmar-only crop and mixed-script pages. Repeated crops/pages are counted separately as samples but not as independent documents.
- The Myanmar-only undertaking crop's seven non-empty reference lines match the corresponding source DOCX text exactly after Unicode NFC normalization and whitespace removal. Its PDF counterpart was not located in the supplied copy, so verification is against the DOCX rather than a paired PDF render. The corrected crop is scored at CER 0.1200 and WER 0.3056; the earlier lower score is not used.
- The Plavix requisition reference was checked against its paired searchable PDF, a 300-DPI PDFium render, and DOCX text. The normalized full reference is about 95.6% aligned with the source text, but 11 of its 23 non-empty lines do not reach 95% character alignment. Those differences remain unresolved, so its score is provisional.
- The cool-storage reference was checked against its best-matching paired searchable PDF, a 300-DPI PDFium render, and DOCX text. Normalized full-text alignment is about 96.1% against the DOCX and 96.1% against the PDF; 5 of 16 non-empty reference lines remain below 95% character alignment. Those differences remain unresolved, so its score is provisional. The supplied copy contains duplicate documents; matching the sample text to the specific duplicate was necessary before assessing its reference.
- These source comparisons do not establish every glyph on the two mixed-script pages. No uncertain text was inferred from OCR output. Treat those two scores as provisional and do not claim three fully independently verified Myanmar references.
- The affected line numbers and unmatched reference-character ranges are explicitly marked `unresolved` in the private line-status record. It stores alignment metadata only, not the source, reference, or OCR text.

## Controlled OCR experiments

The failing samples were tested against their existing references with one OCR variable changed at a time. Per-sample thresholds remain CER `0.10` and WER `0.20`; no candidate passed both.

| Sample | Controlled comparison | Best observed CER / WER (not necessarily the same variant) | Outcome |
|---|---|---:|---|
| Myanmar-only undertaking | Baseline (`mya`, adaptive preprocessing, row recognition): `0.1200 / 0.3056`; turning preprocessing off or switching to `mya+eng` made no difference. Individual-row PSM 7 scored `0.1040 / 0.2778`; PSM 13 reduced WER to `0.2500` but CER rose to `0.1200`. Repeating the PSM 7 approach through the service path returned baseline. Orientation changes degraded results; alternative thresholding reached `0.1120 / 0.3056`. | `0.1040 / 0.2500` | **Fail; no setting adopted.** |
| Plavix requisition | Baseline: `0.5273 / 0.7351`. `mya` only, no preprocessing, alternate orientation/crop, PSM 4/6/11, upscaling, and threshold variants were tried. Individual-row PSM 7 with 1.5x upscaling reached CER `0.5261`; 1.5x PSM 13 reached WER `0.7243`. Both remain far above the limits. | `0.5261 / 0.7243` | **Fail; no setting adopted.** |
| Cool-storage letter | Baseline: `0.4428 / 0.6915`. `mya` only, no preprocessing, alternate orientation, PSM 4/6/11, and Otsu thresholding were tried. Individual-row PSM 7 with 1.5x upscaling reached `0.4353 / 0.6702`, still well above both limits. | `0.4353 / 0.6702` | **Fail; no setting adopted.** |

Experiment configurations and aggregate metrics are retained privately under `D:\Doka\MyanmarBenchmarkExpanded\reference-review`. The line-status record there identifies unresolved reference positions without storing their content. Recognized text, references, image paths, and source filenames are not included in this report. The production OCR configuration and score thresholds were not changed as a result of these experiments.

### Additional local model and row-selection checks

After the controlled comparisons above, the same five private samples were rerun locally with the official Tesseract `tessdata_best` Myanmar model substituted for the installed Myanmar model; preprocessing, page/row layout, language selection, and the English model were held constant. The tested Myanmar model SHA-256 was `629dc3ab7adf4321f329d99f8c737d920308df7519734e36277b773c24df0699`. CER/WER were unchanged for the English sample (`0.0253 / 0.1071`), Myanmar-only sample (`0.1200 / 0.3056`), and Plavix sample (`0.5273 / 0.7351`); the mixed undertaking result regressed from `0.0435 / 0.1760` to `0.0454 / 0.1840`; cool-storage improved only from `0.4428 / 0.6915` to `0.4403 / 0.6915`. No sample newly passed, so this model was not adopted.

A separate local experiment OCRed detected rows individually and selected a language per row using Tesseract's reported confidence. The Myanmar-only sample measured `0.1040 / 0.2778`, still above both strict limits; confidence-based row selection did not improve the two mixed-script samples (best observed CER `0.5273` for Plavix and `0.4378` for cool-storage). A subsequent per-row PSM/scale comparison found only small, non-passing changes: the best independent CER/WER were `0.5261 / 0.7243` for Plavix and `0.4353 / 0.6702` for cool-storage; the Myanmar-only sample's lowest CER and WER (`0.1040` and `0.2500`) came from different settings and both remain over their limits. These experiments did not establish a passing or production-worthy configuration. Aggregate metrics and settings are retained in a private evidence record; raw text and model files remain outside the repository.

## Rendering-font warning

The two newly staged source-page images were rendered at 300 DPI with PDFium; those renders produced no missing-display-font diagnostic. This avoids the prior Poppler `Symbol`/`ArialUnicode` diagnostics for these benchmark images, but does **not** repair Poppler's installed fallback fonts or prove that every production PDF-rendering path is warning-free. The successful full pilot log contained no Poppler font-warning messages.

Adaptive preprocessing had previously left some PDF pages with no normalized text. The OCR service now retries only such pages once using the original, unprocessed render. The successful latest full copied-office pilot logged exactly four such retries, produced non-empty output for all 235 supported files, and had no OCR timeouts. The fallback does not relax benchmark thresholds or modify source files.

## Measured configuration

Tesseract `v5.5.3.20260724`, `eng` and `mya` language data, 300 DPI, OEM 3, configured PSM 11, adaptive Gaussian thresholding, and layout-aware OCR were used. Wide crops use PSM 6; Myanmar-containing portrait/square images use detected text rows with PSM 7. The run used a 120-second OCR timeout. CER uses NFC-normalized grapheme clusters; Myanmar WER uses `mmdt-tokenizer` 0.1.3 grammar-based segmentation, and other-language WER uses whitespace tokenization.

The timeout and source-document counters are recorded by the benchmark implementation. The manifest, source images, source filenames, reference text, OCR text, and credentials remain outside the repository under `D:\Doka`. The repository JSON report contains only sample labels, aggregate/error counts, configuration, and privacy flags.

## Reproduce locally

The private manifest and images are retained under `D:\Doka\MyanmarBenchmarkExpanded`. To rerun with the local private manifest, use the repository benchmark runner and write the output to a private evidence path:

```powershell
$env:OCR_TIMEOUT_SECONDS = '120'
python scripts\ocr_benchmark.py `
  --root 'D:\Doka\MyanmarBenchmarkExpanded\images' `
  --manifest 'D:\Doka\MyanmarBenchmarkExpanded\manifest.verified-private.json' `
  --output 'D:\Doka\MyanmarBenchmarkExpanded\benchmark-reproduced.json'
```

The runner exits `0` when the quality gate passes and `2` when it fails. Do not publish the private manifest or substitute OCR output for the reference text.

## Remaining work

1. Resolve the 11 Plavix and 5 cool-storage reference lines that remain below 95% source-text alignment; mark illegible characters unresolved rather than guessing.
2. Improve OCR on the failing Myanmar samples without changing either threshold, then rerun the same samples and report all outcomes.
3. Keep the older two-empty-PDF finding tied to its earlier run. In the latest short-path pilot, all 211 PDF results were non-empty; the earlier finding is superseded, not an outstanding failure in the latest run.
4. Retain browser acceptance evidence that records the tested commit and deterministic source-tree hashes before and after the full flow.
