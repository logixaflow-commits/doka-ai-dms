import sqlite3
import tempfile
from pathlib import Path

import pytest

from app.core.config import settings
from app.services.consent_store import get_consent_grant, list_audit, list_consents, set_consent


@pytest.fixture
def consent_db(monkeypatch):
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        monkeypatch.setattr(settings, "LOCAL_AUTH_STATE_PATH", root / "auth.sqlite3")
        monkeypatch.setattr(settings, "WORKING_ROOT", root / "workspace")
        monkeypatch.setattr(settings, "SOURCE_ROOT", None)
        yield root


def test_grant_persists_and_is_bound_to_subject_purpose_and_scope(consent_db):
    set_consent(subject_id="alice", actor_id="alice", purpose="document_analysis",
                scope="document:123", granted=True, request_id="req-1")
    assert get_consent_grant(subject_id="alice", purpose="document_analysis", scope="document:123").granted
    assert get_consent_grant(subject_id="bob", purpose="document_analysis", scope="document:123") is None
    assert get_consent_grant(subject_id="alice", purpose="embedding", scope="document:123") is None
    assert get_consent_grant(subject_id="alice", purpose="document_analysis", scope="document:other") is None


def test_revocation_takes_effect_and_retains_history(consent_db):
    set_consent(subject_id="alice", actor_id="alice", purpose="document_analysis",
                scope="document:123", granted=True)
    set_consent(subject_id="alice", actor_id="alice", purpose="document_analysis",
                scope="document:123", granted=False, request_id="req-revoke")
    assert get_consent_grant(subject_id="alice", purpose="document_analysis", scope="document:123") is None
    consent = list_consents(subject_id="alice")
    assert len(consent) == 1
    assert consent[0]["granted"] is False
    events = list_audit(subject_id="alice")
    assert [event["action"] for event in reversed(events)] == ["granted", "revoked"]
    assert events[0]["request_id"] == "req-revoke"


def test_unsupported_purpose_and_empty_scope_fail_closed(consent_db):
    with pytest.raises(ValueError, match="Unsupported"):
        set_consent(subject_id="alice", actor_id="alice", purpose="anything",
                    scope="document:123", granted=True)
    with pytest.raises(ValueError, match="scope"):
        set_consent(subject_id="alice", actor_id="alice", purpose="document_analysis",
                    scope=" ", granted=True)


def test_audit_events_are_append_only(consent_db):
    set_consent(subject_id="alice", actor_id="alice", purpose="document_analysis",
                scope="document:123", granted=True)
    db = sqlite3.connect(str(settings.LOCAL_AUTH_STATE_PATH))
    try:
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            db.execute("UPDATE ai_consent_audit SET action='revoked'")
        db.rollback()
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            db.execute("DELETE FROM ai_consent_audit")
        db.rollback()
    finally:
        db.close()
