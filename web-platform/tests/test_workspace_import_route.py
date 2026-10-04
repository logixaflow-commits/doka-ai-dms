import asyncio

import pytest
from fastapi import BackgroundTasks
from pydantic import ValidationError

from app.api.routes import workspace as workspace_routes
from app.api.routes.workspace import ImportRequest


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
    result = asyncio.run(
        workspace_routes.create_import(ImportRequest(), BackgroundTasks())
    )

    assert calls == [()]
    assert result["session_id"] == "a" * 32
