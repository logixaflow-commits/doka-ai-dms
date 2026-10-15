from cloudflare_worker.b2_quota import evaluate_b2_quota


def test_b2_quota_warns_at_80_percent():
    decision = evaluate_b2_quota(used_bytes=79, requested_bytes=2, quota_bytes=100)
    assert decision.blocked is False
    assert decision.warning == "b2_quota_warning"


def test_b2_quota_blocks_at_95_percent():
    decision = evaluate_b2_quota(used_bytes=94, requested_bytes=1, quota_bytes=100)
    assert decision.blocked is True
    assert decision.warning == "b2_quota_block"


def test_b2_quota_rejects_missing_limit():
    try:
        evaluate_b2_quota(used_bytes=1, requested_bytes=1, quota_bytes=0)
    except ValueError as exc:
        assert "B2_QUOTA_BYTES" in str(exc)
    else:
        raise AssertionError("expected invalid quota")
