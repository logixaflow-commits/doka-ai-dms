"""Regression tests for CodeQL/public-repository security hardening."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.storage import LocalStorageManager, StorageError
from app.services.document_versioning import DocumentVersioningService
from app.services.external_integrations import _validate_webhook_destination


def test_local_storage_rejects_path_escape(tmp_path):
    manager = LocalStorageManager(str(tmp_path / "uploads"))
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")

    with pytest.raises(StorageError):
        manager.download_file(f"file://{outside}")

    assert outside.read_text(encoding="utf-8") == "secret"


def test_local_storage_key_generation_never_uses_filename_traversal(tmp_path):
    manager = LocalStorageManager(str(tmp_path / "uploads"))
    key = manager._generate_key("../category", "../../secret.txt", 7)

    assert ".." not in Path(key).parts
    assert key.startswith("uncategorized/7_document_")


def test_version_service_rejects_files_outside_version_root(tmp_path):
    service = DocumentVersioningService()
    service.versions_storage_path = tmp_path / "versions"
    service.versions_storage_path.mkdir()

    outside = tmp_path / "outside.txt"
    outside.write_text("do not copy", encoding="utf-8")

    with pytest.raises(ValueError, match="outside the version root"):
        service._safe_version_file(str(outside), 1)


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8080/hook",
        "http://localhost:8000/hook",
        "http://10.0.0.1/hook",
        "http://192.168.1.1/hook",
        "file:///etc/passwd",
    ],
)
def test_webhook_destination_rejects_private_or_local_targets(url):
    assert _validate_webhook_destination(url) is not None
