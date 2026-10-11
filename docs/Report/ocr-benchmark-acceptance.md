# OCR benchmark acceptance — tuned run (2026-10-11)

## Result

**PASS — the strict OCR quality gate passes on this three-sample local benchmark.** The fresh run used the same visually checked samples and unchanged thresholds. The benchmark completed all samples without execution errors; the report contains metrics only, not source, reference, or recognized text. This limited sample run does not establish release-wide accuracy.

| Sample language | Samples | Mean CER | Mean WER | Strict per-sample gate (`CER ≤ 0.10`, `WER ≤ 0.20`) |
|---|---:|---:|---:|---|
| `eng` | 1 | 0.0253 | 0.1071 | Pass |
| `mya` | 1 | 0.0880 | 0.1944 | Pass |
| `mya+eng` | 1 | 0.0435 | 0.1600 | Pass |

All aggregate language limits (`CER ≤ 0.30`, `WER ≤ 0.60`) and strict per-sample limits (`CER ≤ 0.10`, `WER ≤ 0.20`) pass in this run. `gate_ready` is `true`; thresholds were not changed.

Compared with the previous PSM 6 run, Myanmar-only improved from CER/WER 0.1120/0.2500 to 0.0880/0.1944; mixed-script improved from 0.5388/1.0240 to 0.0435/0.1600.

## Ground truth and source comparison

- The Myanmar-only image is a crop of the supplied *Untertaking Letter for BL* PDF rendered at 300 DPI. Side-by-side comparison matched the full mixed image to the source rendering (normalized image correlation 1.0) and located the Myanmar crop at source offset `(0, 450)` with correlation `0.999994`; the printed content and layout agree with the DOCX-derived reference used for scoring.
- The `mya+eng` sample is the full rendered PDF page. The English memo reference was also checked against its staged scan.
- Poppler reported missing-display-font warnings for `Symbol` and `ArialUnicode`. The rendered region was legible and checked visually, but font fidelity remains a limitation to resolve before treating this small run as release-quality evidence.
- Original documents, image crops, and text-bearing reference manifest remain under `D:\Doka`; only privacy-scrubbed metrics were written to this repository.

## Measured tuning

The same crops were evaluated across PSM 4, 6, and 11, and raw, adaptive-threshold, Otsu, and CLAHE/Otsu image variants. Results were also checked through the application OCR service rather than relying only on standalone Tesseract output.

| OCR configuration | English CER/WER | Myanmar-only CER/WER | Mixed CER/WER |
|---|---:|---:|---:|
| Previous preprocessing, PSM 6 | 0.0253 / 0.1071 | 0.1120 / 0.2500 | 0.5388 / 1.0240 |
| Previous preprocessing, PSM 11 | 0.0127 / 0.0714 | 0.1120 / 0.2500 | 0.1834 / 0.2160 |
| Adaptive threshold (block 41, C=10), PSM 6 | 0.0253 / 0.1071 | 0.0960 / 0.1944 | 0.2703 / 0.4800 |
| Adaptive threshold (block 31, C=10), PSM 11 | 0.0063 / 0.0357 | 0.1040 / 0.2222 | 0.1928 / 0.2160 |
| Adaptive threshold (block 41; C=5 and PSM 6 for wide crops, C=10 and PSM 11 otherwise) — selected | 0.0253 / 0.1071 | 0.0880 / 0.1944 | 0.1853 / 0.2080 |
| Selected preprocessing and layout, then horizontal row segmentation into one multipage TIFF using PSM 7 for Myanmar page images | 0.0253 / 0.1071 | 0.0880 / 0.1944 | 0.0435 / 0.1600 |

The selected policy applies PSM 6 to wide images (`width/height ≥ 2`) and PSM 11 otherwise. Myanmar-containing portrait/square images are segmented into detected horizontal text rows and passed to Tesseract as one multipage TIFF (PSM 7), so only one Tesseract process starts per image/page. Other images use the layout PSM directly. The application config keeps PSM 11 as its normal default and records these OCR policies; more verified documents are needed before assuming these settings generalize to all layouts.

The benchmark used Tesseract `v5.5.3.20260724`, OEM 3, 300 DPI, with both `eng` and `mya` language data available. CER counts NFC-normalized grapheme clusters; Myanmar WER uses `mmdt-tokenizer` 0.1.3 grammar-based segmentation, and other-language WER uses whitespace tokenization.

## Reproduce locally

The manifest and staged images are private local evidence and are not committed:

```powershell
python scripts\ocr_benchmark.py `
  --root 'D:\Doka\OcrBenchmarkRun\images' `
  --manifest 'D:\Doka\OcrBenchmarkRun\manifest.json' `
  --output 'docs\Report\ocr-benchmark.json'
```

The runner exits `0` when the strict quality gate passes and `2` when it fails.

## Remaining work

1. Add more independently verified English and Myanmar samples, and resolve PDF-rendering font fidelity.
2. Rerun the complete copied-office OCR pilot, including the three previously observed timeouts.
3. Run the full backend/CI checks and review results before considering overall acceptance complete.
