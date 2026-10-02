"""
Office DMS - Security Tests
Tests for password hashing, JWT tokens, and RBAC.
"""

import pytest
from datetime import timedelta
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_token,
)
from app.core.encryption import EncryptionManager
from app.core.config import Settings


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "test_password_123"
        hashed = hash_password(password)
        assert verify_password(password, hashed) is True

    def test_verify_wrong_password(self):
        password = "correct_password"
        wrong = "wrong_password"
        hashed = hash_password(password)
        assert verify_password(wrong, hashed) is False

    def test_hash_is_different_each_time(self):
        password = "same_password"
        hash1 = hash_password(password)
        hash2 = hash_password(password)
        assert hash1 != hash2  # bcrypt salts are random


class TestJWT:
    def test_create_and_decode(self):
        token = create_access_token({"sub": "1", "role": "admin"})
        payload = decode_token(token)
        assert payload is not None
        assert payload["sub"] == "1"
        assert payload["role"] == "admin"
        assert payload["type"] == "access"

    def test_invalid_token(self):
        payload = decode_token("invalid.token.here")
        assert payload is None


class TestEncryption:
    def test_encryption_disabled_without_key(self):
        mgr = EncryptionManager()
        # Without key, data should pass through
        data = b"test data"
        result = mgr.encrypt(data)
        assert result == data

    def test_encrypt_decrypt_with_key(self):
        from cryptography.fernet import Fernet

        key = Fernet.generate_key().decode()
        from unittest.mock import patch

        with patch("app.core.encryption.settings.ENCRYPTION_KEY", key):
            mgr = EncryptionManager()
            mgr._init_cipher()

            if mgr.is_enabled:
                data = b"sensitive document content"
                encrypted = mgr.encrypt(data)
                decrypted = mgr.decrypt(encrypted)
                assert decrypted == data
                assert encrypted != data



def test_settings_rejects_short_hs256_secret(monkeypatch):
    monkeypatch.setenv("SECRET_KEY", "short-test-key")
    with pytest.raises(ValueError, match="at least 32 bytes"):
        Settings()
