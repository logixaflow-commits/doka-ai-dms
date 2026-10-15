import threading
from concurrent.futures import ThreadPoolExecutor

import pytest
from fastapi import BackgroundTasks, FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.routes import workspace as workspace_routes
from app.api.routes.workspace import ImportRequest
from app.core.config import settings
from app.core.supabase_auth import require_local_workspace_user
from app.services.safe_workspace_service import safe_workspace_service


def test_import_route_rejects_source_override(tmp_path, monkeypatch):
    outside = tmp_path / "outside"
    outside.mkdir()
    with pytest.raises(ValidationError, match="Extra inputs are not permitted"):
        ImportRequest.model_validate({"source": str(outside)})

    calls = []

    def create_import(*args):
        calls.append(args)
        return {"session_id": "a" * 32}

    monkeypatch.setattr(
        workspace_routes.safe_workspace_service, "create_import", create_import
    )
    result = workspace_routes.create_import(ImportRequest(), BackgroundTasks())

    assert calls == [()]
    assert result["session_id"] == "a" * 32

    monkeypatch.setattr(
        workspace_routes.safe_workspace_service, "run_import", lambda _session_id: None
    )
    app = FastAPI()
    app.include_router(workspace_routes.router)
    app.dependency_overrides[require_local_workspace_user] = lambda: {
        "user_id": "synthetic-test-user"
    }
    with TestClient(app) as client:
        rejected = client.post("/api/workspace/imports", json={"source": str(outside)})
        accepted = client.post("/api/workspace/imports", json={})

    assert rejected.status_code == 422
    assert rejected.json()["detail"] == [
        {
            "type": "extra_forbidden",
            "loc": ["body", "source"],
            "msg": "Extra inputs are not permitted",
            "input": str(outside),
        }
    ]
    assert accepted.status_code == 200
    assert accepted.json()["session_id"] == "a" * 32
    assert calls == [(), ()]


@pytest.mark.parametrize("operation", ["import", "scan"])
def test_workspace_status_and_health_routes_remain_responsive(
    operation, tmp_path, monkeypatch
):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    workspace.mkdir()
    source.mkdir()
    (source / "synthetic.txt").write_text("synthetic api payload", encoding="utf-8")
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)
    service = safe_workspace_service

    if operation == "scan":
        session = service.create_import()
        assert service.run_import(session["session_id"])["state"] == "completed"
    else:
        session = None

    app = FastAPI()
    app.include_router(workspace_routes.router)
    app.dependency_overrides[require_local_workspace_user] = lambda: {
        "user_id": "synthetic-test-user"
    }

    @app.get("/health")
    async def health():
        return {"status": "healthy"}

    started = threading.Event()
    release = threading.Event()
    operation_errors = []
    if operation == "import":
        original_open = service._open_source_file

        def blocked_open(source_root, path):
            started.set()
            if not release.wait(timeout=5):
                raise TimeoutError("Test did not release the API import.")
            return original_open(source_root, path)

        monkeypatch.setattr(service, "_open_source_file", blocked_open)
    else:
        original_files = service._files

        def blocked_files(root):
            for path in original_files(root):
                started.set()
                if not release.wait(timeout=5):
                    raise TimeoutError("Test did not release the API scan.")
                yield path

        monkeypatch.setattr(service, "_files", blocked_files)

    def request(method, path):
        with TestClient(app) as client:
            return getattr(client, method)(path)

    def run_operation():
        try:
            with TestClient(app) as client:
                if operation == "import":
                    response = client.post("/api/workspace/imports", json={})
                else:
                    response = client.post(
                        f"/api/workspace/imports/{session['session_id']}/scan"
                    )
                if response.status_code != 200:
                    operation_errors.append(response.text)
        except Exception as exc:
            operation_errors.append(exc)

    with ThreadPoolExecutor(max_workers=3) as requests:
        operation_request = requests.submit(run_operation)
        try:
            assert started.wait(timeout=3)
            active_session_id = (
                session["session_id"]
                if session
                else service.list_sessions(limit=1)[0]["session_id"]
            )
            status_response = requests.submit(
                request, "get", f"/api/workspace/imports/{active_session_id}"
            ).result(timeout=2)
            health_response = requests.submit(request, "get", "/health").result(timeout=2)
            assert status_response.status_code == 200
            assert status_response.json()["state"] == (
                "running" if operation == "import" else "scanning"
            )
            assert health_response.status_code == 200
            assert health_response.json()["status"] == "healthy"
        finally:
            release.set()
        operation_request.result(timeout=5)

    assert not operation_errors
