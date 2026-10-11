# OCR benchmark acceptance — Gate 3

## Pass criteria

- The manifest includes separately labelled `mya` and `eng` samples. A `mya+eng` mixed-script sample is useful additional coverage but does not count as either language-specific benchmark.
- Tesseract is executable in the acceptance environment and reports both `mya` and `eng` language packs.
- Every sample finishes within configured OCR resource/time limits; errors/timeouts remain visible and block the gate.
- Per-language mean CER is at most `0.30` and mean WER at most `0.60`.
- Ground-truth Myanmar reference text has been visually checked against the rendered scan. Do not adjust the reference solely to improve the score.
- Run on a privacy-approved copy; the JSON report must not contain reference or recognized document text.
- After benchmark issues are fixed, rerun the complete copied-office pilot, including the three previously observed OCR timeouts.

## Reproducible run

Create a manifest from `Phase0_Evidence/ocr_benchmark/manifest.example.json` and replace the placeholders with paths to approved copied samples and visually verified reference text. Use distinct `language: "mya"` and `language: "eng"` entries. Keep samples and reports outside the original office-data directory.

```bash
python scripts/ocr_benchmark.py \
  --root /absolute/path/to/approved-copied-samples \
  --manifest /absolute/path/to/ocr-manifest.json \
  --output /absolute/path/to/evidence/ocr-benchmark.json
```

The command exits `0` only when the benchmark gate is ready; otherwise it exits `2`. Keep the toolchain metadata, sample IDs, per-language metrics, errors, thresholds, and privacy flags with the release evidence. Do not commit scan files, ground-truth text, recognized text, personal data, or credentials.

## Current status (2026-10-11)

**PENDING / BLOCKED — no new real OCR run has been claimed.** The preserved report contains five English-only samples and one mixed `mya+eng` sample. English aggregate CER/WER are `0.1808` / `0.3865`; the mixed sample CER/WER are `0.7994` / `1.7143`. The mixed sample fails thresholds and cannot establish Myanmar-only quality. The connected disposable workspace used for code verification has no Tesseract executable and contains no benchmark scan assets, so live accuracy, reference-image comparison, resource timings, and the three-timeout resolution must be completed on the provisioned local acceptance machine.
