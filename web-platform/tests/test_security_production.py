from cryptography.fernet import Fernet
import pytest

from app.core.security_production import ProductionSecurity


def test_encrypt_sensitive_data_requires_configured_key(monkeypatch):
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

    with pytest.raises(ValueError, match="ENCRYPTION_KEY must be configured"):
        ProductionSecurity().encrypt_sensitive_data("private data")


def test_encrypt_sensitive_data_rejects_invalid_fernet_key(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEY", "not-a-valid-fernet-key")

    with pytest.raises(ValueError, match="ENCRYPTION_KEY must be a valid Fernet key"):
        ProductionSecurity().encrypt_sensitive_data("private data")


def test_decrypt_sensitive_data_requires_configured_key(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    encrypted = ProductionSecurity().encrypt_sensitive_data("private data")
    monkeypatch.delenv("ENCRYPTION_KEY", raising=False)

    with pytest.raises(ValueError, match="ENCRYPTION_KEY must be configured"):
        ProductionSecurity().decrypt_sensitive_data(encrypted)


def test_sensitive_data_encryption_round_trip(monkeypatch):
    monkeypatch.setenv("ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    security = ProductionSecurity()

    encrypted = security.encrypt_sensitive_data("private data")

    assert encrypted != "private data"
    assert security.decrypt_sensitive_data(encrypted) == "private data"
