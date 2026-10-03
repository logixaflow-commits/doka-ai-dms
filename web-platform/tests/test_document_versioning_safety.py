import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from app.services.document_versioning import (
    DocumentVersioningService,
    VersionMetadataError,
)


def _service(tmp_path):
    service = DocumentVersioningService.__new__(DocumentVersioningService)
    service.versions_storage_path = tmp_path / "versions"
    service.versions_storage_path.mkdir()
    return service


def test_concurrent_version_creation_serializes_and_preserves_all_versions(tmp_path):
    source = tmp_path / "source.txt"
    source.write_text("representative test data", encoding="utf-8")
    service = _service(tmp_path)

    def create(index):
        return service.create_version(
            document_id=7,
            file_path=str(source),
            user_id=index + 1,
            comment=f"concurrent-{index}",
        )

    with ThreadPoolExecutor(max_workers=8) as pool:
        versions = list(pool.map(create, range(8)))

    numbers = sorted(version.version_number for version in versions)
    assert numbers == list(range(1, 9))

    metadata_path = service.versions_storage_path / "7" / "versions.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    assert sorted(item["version_number"] for item in metadata) == list(range(1, 9))
    assert len({item["id"] for item in metadata}) == 8


def test_corrupt_version_metadata_raises_diagnostic_instead_of_empty_history(tmp_path):
    service = _service(tmp_path)
    document_dir = service.versions_storage_path / "9"
    document_dir.mkdir()
    (document_dir / "versions.json").write_text("{not-json", encoding="utf-8")

    with pytest.raises(VersionMetadataError, match="unreadable for document 9"):
        service.get_document_versions(9)
