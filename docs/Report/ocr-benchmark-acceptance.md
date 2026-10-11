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
- The existing undertaking reference was visually compared with its source PDF page and paired DOCX. Rendering the source again with PDFium shifted the page height by one pixel; the crop was adjusted to that rendered page before scoring. On the corrected crop, the unchanged strict gate fails (CER 0.1200, WER 0.3056); the earlier lower score is not used.
- The two additional Myanmar-bearing references were derived from searchable PDF text and compared with paired DOCX text and rendered pages. Differences in extraction order/content remain, and a complete manual, line-by-line transcription check has not been recorded. Treat these two scores as provisional rather than independently ground-truthed accuracy claims.
- Do not use the expanded set to claim that Myanmar OCR quality is independently established across all three sources. Complete the manual reference verification before treating those samples as validated ground truth.

## Rendering-font warning

The two newly staged source-page images were rendered at 300 DPI with PDFium; those renders produced no missing-display-font diagnostic. This avoids the prior Poppler `Symbol`/`ArialUnicode` diagnostics for these benchmark images, but does **not** repair Poppler's installed fallback fonts or prove that every production PDF-rendering path is warning-free. The successful full pilot log contained no Poppler font-warning messages.

Adaptive preprocessing had previously left some PDF pages with no normalized text. The OCR service now retries only such pages once using the original, unprocessed render. The successful full copied-office pilot used this fallback four times, produced non-empty output for all 235 supported files, and had no OCR timeouts. The fallback does not relax benchmark thresholds or modify source files.

## Measured configuration

Tesseract `v5.5.3.20260724`, `eng` and `mya` language data, 300 DPI, OEM 3, configured PSM 11, adaptive Gaussian thresholding, and layout-aware OCR were used. Wide crops use PSM 6; Myanmar-containing portrait/square images use detected text rows with PSM 7. The run used a 120-second OCR timeout. CER uses NFC-normalized grapheme clusters; Myanmar WER uses `mmdt-tokenizer` 0.1.3 grammar-based segmentation, and other-language WER uses whitespace tokenization.

The timeout and source-document counters are recorded by the benchmark implementation. The manifest, source images, source filenames, reference text, OCR text, and credentials remain outside the repository under `D:\Doka`. The committed JSON contains only anonymized sample labels, aggregate/error counts, configuration, and privacy flags.

## Reproduce locally

The private manifest and images are retained under `D:\Doka\MyanmarBenchmarkExpanded`. To rerun with the local private manifest, use the repository benchmark runner and write the output to a private evidence path:

```powershell
python scripts\ocr_benchmark.py `
  --root 'D:\Doka\MyanmarBenchmarkExpanded\images' `
  --manifest 'D:\Doka\MyanmarBenchmarkExpanded\manifest.verified-private.json' `
  --output 'D:\Doka\MyanmarBenchmarkExpanded\benchmark-reproduced.json'
```

The runner exits `0` when the quality gate passes and `2` when it fails. Do not publish the private manifest or substitute OCR output for the reference text.

## Remaining work

1. Manually verify each new Myanmar-bearing reference line by line against the source render; record unresolved characters instead of guessing.
2. Improve OCR on the failing Myanmar samples without changing either threshold, then rerun the same samples and report all outcomes.
3. Investigate the two full-pilot PDFs that returned no text and rerun the entire copied-office pilot only if a specific, validated fix is made.
4. Verify the complete browser workflow in Chromium, including unchanged source hashes.
