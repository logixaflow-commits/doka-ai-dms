# OCR benchmark acceptance — tuned run (2026-10-11)

## Result

**FAIL — the strict OCR quality gate remains closed.** This fresh run used the same three verified samples and unchanged thresholds. The benchmark completed all samples without execution errors; the report contains metrics only, not source, reference, or recognized text.

| Sample language | Samples | Mean CER | Mean WER | Strict per-sample gate (`CER ≤ 0.10`, `WER ≤ 0.20`) |
|---|---:|---:|---:|---|
| `eng` | 1 | 0.0063 | 0.0357 | Pass |
| `mya` | 1 | 0.1040 | 0.2222 | **Fail** |
| `mya+eng` | 1 | 0.1928 | 0.2160 | **Fail** |

All aggregate language limits (`CER ≤ 0.30`, `WER ≤ 0.60`) pass in this run. The stricter per-sample gate still has four failures across the two Myanmar samples; `gate_ready` correctly remains `false`. Thresholds were not changed.

Compared with the previous PSM 6 run, English CER/WER improved from 0.0253/0.1071, Myanmar-only from 0.1120/0.2500, and mixed-script from 0.5388/1.0240. The mixed-page change is substantial, but it does not satisfy the strict gate.

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
| Adaptive threshold (Gaussian, block 31, C=10), PSM 11 — selected | 0.0063 / 0.0357 | 0.1040 / 0.2222 | 0.1928 / 0.2160 |

PSM 11 improved all three samples compared with the former PSM 6 pipeline. The selected adaptive-threshold variant further improved English and Myanmar-only results and improved the three-sample mean WER; its mixed-page CER is slightly higher than the PSM 11 result using the former preprocessing, while remaining substantially better than the original PSM 6 baseline. The application config now uses PSM 11 and adaptive thresholding. More verified documents are needed before assuming these settings generalize to all layouts.

The benchmark used Tesseract `v5.5.3.20260724`, OEM 3, 300 DPI, with both `eng` and `mya` language data available. CER counts NFC-normalized grapheme clusters; Myanmar WER uses `mmdt-tokenizer` 0.1.3 grammar-based segmentation, and other-language WER uses whitespace tokenization.

## Reproduce locally

The manifest and staged images are private local evidence and are not committed:

```powershell
python scripts\ocr_benchmark.py `
  --root 'D:\Doka\OcrBenchmarkRun\images' `
  --manifest 'D:\Doka\OcrBenchmarkRun\manifest.json' `
  --output 'docs\Report\ocr-benchmark.json'
```

The runner exits `2` while the strict quality gate is failing; this is expected.

## Remaining work

1. Continue improving Myanmar-only and mixed-script recognition without weakening the thresholds.
2. Add more independently verified English and Myanmar samples, and resolve PDF-rendering font fidelity.
3. Rerun the complete copied-office OCR pilot, including the three previously observed timeouts.
4. Run the full backend/CI checks and review results before considering acceptance complete.
