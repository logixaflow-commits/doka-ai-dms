from app.services.ocr_comparison import compare_batch, compare_ocr_text

def test_exact_match_passes_and_diff_is_equal():
    result = compare_ocr_text("မြန်မာစာ DMS", "မြန်မာစာ DMS", language="mya+eng")
    assert result["status"] == "PASS"
    assert result["metrics"]["cer"] == 0
    assert result["metrics"]["wer"] == 0
    assert all(part["kind"] == "equal" for part in result["diff"])

def test_changed_text_requires_review_and_highlights_difference():
    result = compare_ocr_text("Invoice total 100", "Invoice total 700", language="eng", max_cer=0.01, max_wer=0.01)
    assert result["status"] == "REVIEW"
    assert any(part["kind"] != "equal" for part in result["diff"])

def test_empty_ocr_output_fails_closed():
    result = compare_ocr_text("Verified reference", "  ", language="eng")
    assert result["status"] == "FAIL"

def test_batch_does_not_claim_partial_pass_is_complete():
    result = compare_batch([
        {"file_id": "a", "reference": "same", "prediction": "same", "language": "eng"},
        {"file_id": "b", "reference": "expected text", "prediction": "", "language": "eng"},
    ])
    assert result["total"] == 2
    assert result["status_counts"] == {"PASS": 1, "REVIEW": 0, "FAIL": 1}
    assert result["all_passed"] is False
    assert "reference" not in result

def test_duplicate_file_ids_are_rejected():
    import pytest
    with pytest.raises(ValueError, match="Duplicate file_id"):
        compare_batch([
            {"file_id": "same", "reference": "a", "prediction": "a"},
            {"file_id": "same", "reference": "b", "prediction": "b"},
        ])

def test_missing_reference_is_fail_in_batch():
    result = compare_batch([{"file_id": "x", "prediction": "some OCR"}])
    assert result["status_counts"]["FAIL"] == 1
