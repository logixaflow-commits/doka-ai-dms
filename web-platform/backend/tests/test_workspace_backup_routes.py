from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes import workspace as workspace_routes
from app.core.config import settings
from app.core.supabase_auth import require_local_workspace_user
from app.services.workspace_backup_service import WorkspaceBackupService


def _client():
    app = FastAPI()
    app.include_router(workspace_routes.router)
    app.dependency_overrides[require_local_workspace_user] = lambda: {
        "user_id": "synthetic-backup-test-user"
    }
    return TestClient(app)


def _configure_roots(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    backups = tmp_path / "backups"
    workspace.mkdir()
    backups.mkdir()
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "BACKUP_ROOT", backups)
    return workspace, backups


def test_prune_route_requires_confirmation_and_supports_preview(
    tmp_path, monkeypatch
):
    _configure_roots(tmp_path, monkeypatch)
    WorkspaceBackupService().create()

    with _client() as client:
        missing_confirmation = client.post("/api/workspace/backups/prune")
        false_confirmation = client.post(
            "/api/workspace/backups/prune?confirm=false"
        )
        preview = client.post(
            "/api/workspace/backups/prune?dry_run=true"
        )
        confirmed = client.post(
            "/api/workspace/backups/prune?confirm=true"
        )

    assert missing_confirmation.status_code == 400
    assert missing_confirmation.json()["detail"] == "Invalid request."
    assert false_confirmation.status_code == 400
    assert preview.status_code == 200
    assert preview.json()["dry_run"] is True
    assert preview.json()["removed"] == []
    assert confirmed.status_code == 200
    assert confirmed.json()["dry_run"] is False


def test_restore_route_confirmation_preserves_integrity_validation(
    tmp_path, monkeypatch
):
    _, backups = _configure_roots(tmp_path, monkeypatch)
    manifest = WorkspaceBackupService().create()
    archive = backups / Path(manifest["archive"]).name
    with archive.open("ab") as handle:
        handle.write(b"tampered")

    with _client() as client:
        missing_confirmation = client.post(
            f"/api/workspace/backups/restore?archive_name={archive.name}"
        )
        confirmed = client.post(
            f"/api/workspace/backups/restore?archive_name={archive.name}&confirm=true"
        )

    assert missing_confirmation.status_code == 400
    assert "confirmation" in missing_confirmation.json()["detail"]
    assert confirmed.status_code == 400
    assert confirmed.json()["detail"] == "Invalid request."
    assert not list((tmp_path / "workspace" / "Recovery").glob("restore_*"))


def test_restore_route_accepts_confirmation_and_restores_to_recovery(
    tmp_path, monkeypatch
):
    workspace, _ = _configure_roots(tmp_path, monkeypatch)
    (workspace / "active.txt").write_text("original", encoding="utf-8")
    manifest = WorkspaceBackupService().create()
    (workspace / "active.txt").write_text("current", encoding="utf-8")
    archive_name = Path(manifest["archive"]).name

    with _client() as client:
        response = client.post(
            f"/api/workspace/backups/restore?archive_name={archive_name}&confirm=true"
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["active_workspace_changed"] is False
    assert (workspace / "active.txt").read_text(encoding="utf-8") == "current"
    recovery_file = Path(payload["recovery_path"]) / "active.txt"
    assert recovery_file.read_text(encoding="utf-8") == "original"
