import hashlib

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, settings
from app.core.local_security import create_local_access_token
from app.main import create_app
from app.services.safe_workspace_service import safe_workspace_service
from app.services.organization_planner import organization_planner


def _configure_roots(monkeypatch, tmp_path):
    source = tmp_path / "source"
    working = tmp_path / "workspace"
    source.mkdir()
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "WORKING_ROOT", working)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)
    return source, working


def test_settings_canonicalizes_source_root(monkeypatch, tmp_path):
    source = tmp_path / "source"
    source.mkdir()
    monkeypatch.setenv("SOURCE_ROOT", str(tmp_path / "unused" / ".." / "source"))

    loaded = Settings()

    assert loaded.SOURCE_ROOT == source.resolve()


def test_source_validation_rejects_outside_traversal_and_sibling_prefix(
    monkeypatch, tmp_path
):
    source, _working = _configure_roots(monkeypatch, tmp_path)
    outside = tmp_path / "source-sibling"
    outside.mkdir()
    inside = source / "inside"
    inside.mkdir()

    assert safe_workspace_service.validate_source() == source.resolve()
    assert safe_workspace_service.validate_source(inside) == inside.resolve()

    for path in (outside, source / ".." / "source-sibling"):
        with pytest.raises(ValueError) as error:
            safe_workspace_service.validate_source(path)
        assert str(source) not in str(error.value)
        assert str(outside) not in str(error.value)


@pytest.mark.parametrize(
    ("flag", "unsafe_value"),
    [("ALLOW_SOURCE_WRITE", True), ("ORIGINAL_READ_ONLY", False)],
)
def test_source_validation_enforces_read_only_settings(
    monkeypatch, tmp_path, flag, unsafe_value
):
    _configure_roots(monkeypatch, tmp_path)
    monkeypatch.setattr(settings, flag, unsafe_value)

    with pytest.raises(ValueError, match="must remain"):
        safe_workspace_service.validate_source()


def test_source_validation_rejects_workspace_overlap(monkeypatch, tmp_path):
    source, _working = _configure_roots(monkeypatch, tmp_path)
    monkeypatch.setattr(settings, "WORKING_ROOT", source / "workspace")

    with pytest.raises(ValueError, match="overlap"):
        safe_workspace_service.validate_source()


def test_source_symlink_escape_is_rejected(monkeypatch, tmp_path):
    source, _working = _configure_roots(monkeypatch, tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    try:
        (source / "escape").symlink_to(outside, target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"Directory symlink creation is unavailable on this Windows host: {exc}")

    with pytest.raises(ValueError, match="outside the configured source root"):
        safe_workspace_service.validate_source(source / "escape")


def test_import_copies_and_verifies_synthetic_source_without_changing_originals(
    monkeypatch, tmp_path
):
    source, _working = _configure_roots(monkeypatch, tmp_path)
    original = source / "folder" / "synthetic.txt"
    original.parent.mkdir()
    original.write_bytes(b"synthetic source content\n")
    before = original.stat()

    session = safe_workspace_service.create_import()
    result = safe_workspace_service.run_import(session["session_id"])
    manifest = safe_workspace_service._read(
        safe_workspace_service._json_path(session["session_id"], "manifest.json")
    )
    copied = (
        safe_workspace_service._dir(session["session_id"])
        / "source_copy"
        / "folder"
        / "synthetic.txt"
    )

    assert result["state"] == "completed"
    assert result["files_copied"] == 1
    assert copied.read_bytes() == b"synthetic source content\n"
    assert hashlib.sha256(copied.read_bytes()).hexdigest() == manifest["files"][
        "folder/synthetic.txt"
    ]["sha256"]
    assert manifest["files"]["folder/synthetic.txt"]["verified"] is True
    after = original.stat()
    assert original.read_bytes() == b"synthetic source content\n"
    assert (after.st_size, after.st_mtime_ns, after.st_mode) == (
        before.st_size,
        before.st_mtime_ns,
        before.st_mode,
    )


def test_source_symlink_replacement_between_discovery_and_open_is_not_copied(
    monkeypatch, tmp_path
):
    source, _working = _configure_roots(monkeypatch, tmp_path)
    original = source / "synthetic.txt"
    original.write_bytes(b"inside source")
    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"outside sentinel")

    probe = tmp_path / "symlink-probe"
    try:
        probe.symlink_to(outside)
    except (OSError, NotImplementedError) as exc:
        pytest.skip(f"File symlink creation is unavailable on this Windows host: {exc}")
    else:
        probe.unlink()

    def enumerate_then_replace(_root):
        yield original
        original.unlink()
        original.symlink_to(outside)

    monkeypatch.setattr(safe_workspace_service, "_files", enumerate_then_replace)
    try:
        session = safe_workspace_service.create_import()
        result = safe_workspace_service.run_import(session["session_id"])
        copied = (
            safe_workspace_service._dir(session["session_id"])
            / "source_copy"
            / "synthetic.txt"
        )

        assert result["state"] == "completed_with_errors"
        assert result["files_failed"] == 1
        assert not copied.exists()
        assert outside.read_bytes() == b"outside sentinel"
    finally:
        if original.is_symlink():
            original.unlink()
        if not original.exists():
            original.write_bytes(b"inside source")


def test_import_api_rejects_client_supplied_source_paths(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "LOCAL_AUTH_STATE_PATH", tmp_path / "auth.sqlite3")
    monkeypatch.setattr(settings, "ENVIRONMENT", "test")
    token = create_local_access_token("batch0-local-admin")
    response = TestClient(create_app()).post(
        "/api/workspace/imports",
        json={"source": str(tmp_path / "untrusted-source")},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 422


def test_organization_apply_rejects_duplicate_or_oversized_approval_lists():
    with pytest.raises(ValueError, match="No approved files"):
        organization_planner.apply("synthetic-session", [])
    with pytest.raises(ValueError, match="At most 500"):
        organization_planner.apply("synthetic-session", [f"file-{i}" for i in range(501)])
    with pytest.raises(ValueError, match="Duplicate approved paths"):
        organization_planner.apply("synthetic-session", ["same.txt", "same.txt"])
