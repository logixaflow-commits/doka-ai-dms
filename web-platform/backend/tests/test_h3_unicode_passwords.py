import bcrypt
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.passwords import hash_password, verify_password
from app.main import create_app


@pytest.mark.parametrize(
    "password",
    [
        "ASCII-Pass123!",
        "မြန်မာစကားဝှက်၁၂၃!",
        "日本語パスワード-123!",
        "한국어비밀번호-123!",
        "Mixed-ASCII-မြန်မာ-123!",
        "Mixed-ASCII-မြန်မာ-한국어-123!",
    ],
)
def test_password_hashing_preserves_ascii_and_unicode(password):
    password_hash = hash_password(password)

    assert verify_password(password, password_hash) == (True, False)
    assert verify_password(password + "wrong", password_hash) == (False, False)


def test_visually_similar_unicode_sequences_remain_distinct():
    composed = "café-Password9!"
    decomposed = "cafe\u0301-Password9!"
    password_hash = hash_password(composed)

    assert verify_password(composed, password_hash) == (True, False)
    assert verify_password(decomposed, password_hash) == (False, False)
    assert verify_password(composed + " ", password_hash) == (False, False)
    assert verify_password(composed.swapcase(), password_hash) == (False, False)


def test_registration_login_round_trip_and_existing_bcrypt_hash_compatibility():
    password = "Registered-မြန်မာ-Password9!"
    registered_hash = hash_password(password)
    existing_format_hash = bcrypt.hashpw(
        password.encode("utf-8"), bcrypt.gensalt()
    ).decode("utf-8")

    assert verify_password(password, registered_hash) == (True, False)
    assert verify_password(password, existing_format_hash) == (True, True)


def test_empty_and_malformed_password_inputs_fail_safely():
    with pytest.raises(ValueError, match="non-empty"):
        hash_password("")
    with pytest.raises(ValueError, match="non-empty"):
        hash_password(None)
    with pytest.raises(ValueError, match="valid Unicode"):
        hash_password("\ud800")
    assert verify_password("", "not-a-valid-bcrypt-hash") == (False, False)
    assert verify_password(None, "not-a-valid-bcrypt-hash") == (False, False)
    assert verify_password("password", None) == (False, False)
    assert verify_password("password", "malformed") == (False, False)


def test_unicode_passwords_over_bcrypt_byte_limit_are_prehash_supported():
    long_password = "မြ" * 25
    assert len(long_password.encode("utf-8")) > 72
    legacy_truncated_hash = bcrypt.hashpw(
        long_password.encode("utf-8")[:72], bcrypt.gensalt()
    ).decode("utf-8")

    password_hash = hash_password(long_password)
    assert verify_password(long_password, password_hash) == (True, False)
    assert verify_password(long_password, legacy_truncated_hash) == (False, False)
    assert verify_password(long_password + "different", legacy_truncated_hash) == (
        False,
        False,
    )


def test_local_unicode_password_login_round_trip_and_exact_comparison(
    monkeypatch, tmp_path
):
    password = "မြန်မာ-한국어-Local-Password123!"
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    monkeypatch.setattr(settings, "LOCAL_ADMIN_USERNAME", "unicode-admin")
    monkeypatch.setattr(settings, "BOOTSTRAP_ADMIN_PASSWORD", password)
    monkeypatch.setattr(settings, "LOCAL_AUTH_STATE_PATH", tmp_path / "auth.sqlite3")
    client = TestClient(create_app())

    login = client.post(
        "/api/auth/login",
        json={"username": "unicode-admin", "password": password},
    )
    assert login.status_code == 200
    token = login.json()["access_token"]
    assert client.get(
        "/api/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    ).status_code == 200
    assert client.post(
        "/api/auth/login",
        json={"username": "unicode-admin", "password": password + "x"},
    ).status_code == 401
    assert client.post(
        "/api/auth/login",
        json={"username": "unicode-admin", "password": ""},
    ).status_code == 401
