# Doka Personal Local OCR Benchmark

This benchmark measures Myanmar/English OCR quality on a **copy** of representative office documents. It does not send documents to an external AI provider and does not modify the sample files.

## Prepare a safe sample set

1. Copy representative PDF/image pages into a dedicated folder outside the active Doka workspace.
2. Create a JSON manifest. Keep reference transcriptions accurate; use one record per page/image.

```json
{
  "samples": [
    {
      "id": "mya-invoice-001",
      "path": "invoices/page-001.png",
      "mime_type": "image/png",
      "language": "mya+eng",
      "reference": "မင်္ဂလာပါ Example Company"
    },
    {
      "id": "eng-form-001",
      "path": "forms/page-001.pdf",
      "mime_type": "application/pdf",
      "language": "eng",
      "reference": "Application Form"
    }
  ]
}
```

Paths must be relative to the sample root. Absolute paths, traversal segments and symlinks are rejected.

## Run the benchmark

From the repository root:

```bash
python scripts/ocr_benchmark.py \
  --root /path/to/DokaPilotCopy \
  --manifest /path/to/ocr-ground-truth.json \
  --output /path/to/reports/ocr-benchmark.json
```

The output report must be outside the sample root. The CLI prints sample counts and aggregate scores.

## Metrics

- **CER (Character Error Rate):** character-level edit distance divided by reference character count.
- **WER (Word Error Rate):** whitespace-token word edit distance divided by reference word count.
- Results are grouped by the manifest's `language` field. A score of 0 means an exact normalized match; lower is better.
- Normalization uses Unicode NFC, case-folding and whitespace collapse. Preserve the original ground-truth file separately.

## Privacy and interpretation

- The report contains sample IDs, language, scores, error types and aggregate metrics only.
- Recognized text and reference text are never copied into the report.
- The script refuses to write its report inside the sample directory.
- The benchmark measures OCR quality only; it does not approve organization proposals or modify documents.
- A meaningful Phase 2 pilot still requires enough representative Myanmar and English samples, manual review of low-scoring pages, and a recorded acceptance threshold chosen by the project owner.
