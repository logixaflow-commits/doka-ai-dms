from pathlib import Path
import json
import pytest
from app.services.organization_planner import OrganizationPlanner, normalize_stem
from app.core.config import settings
from app.services.safe_workspace_service import SafeWorkspaceService


def test_normalize_stem_groups_common_versions():
    base = normalize_stem("Invoice ABC 2025.pdf")
    assert base == normalize_stem("Invoice ABC 2025 copy.pdf")
    assert base == normalize_stem("Invoice ABC 2025 v2.pdf")
    assert base == normalize_stem("Invoice ABC 2025 final.pdf")


def test_normalize_stem_keeps_different_documents_separate():
    assert normalize_stem("Invoice ABC.pdf") != normalize_stem("Invoice XYZ.pdf")


def test_organization_apply_and_undo_preserves_source(tmp_path, monkeypatch):
    from app.core.config import settings
    from app.services.organization_planner import OrganizationPlanner
    from app.services.safe_workspace_service import SafeWorkspaceService

    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    final = workspace / "Final"
    workspace.mkdir()
    source.mkdir()
    (source / "Invoice ABC 2025.txt").write_text("Invoice ABC 2025\nPayment due", encoding="utf-8")
    original = (source / "Invoice ABC 2025.txt").read_bytes()

    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "FINAL_ROOT", final)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    workspace_service = SafeWorkspaceService()
    created = workspace_service.create_import()
    workspace_service.run_import(created["session_id"])
    workspace_service.scan(created["session_id"])
    planner = OrganizationPlanner()
    plan = planner.plan(created["session_id"])

    approved = [
        item["relative_path"]
        for item in plan["proposals"]
        if item["action"] == "suggest_move"
    ]
    result = planner.apply(created["session_id"], approved)
    assert any(item["status"] == "copied" for item in result["results"])
    assert (source / "Invoice ABC 2025.txt").read_bytes() == original

    undo = planner.undo(created["session_id"])
    assert any(item["status"] == "removed" for item in undo["results"])
    assert (source / "Invoice ABC 2025.txt").read_bytes() == original


def test_organization_apply_rejects_tampered_target(tmp_path, monkeypatch):
    source = tmp_path / "source"
    workspace = tmp_path / "workspace"
    source.mkdir()
    (source / "invoice.txt").write_text("invoice payment", encoding="utf-8")
    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "FINAL_ROOT", workspace / "Final")
    monkeypatch.setattr(settings, "QUARANTINE_ROOT", workspace / "Quarantine")

    service = SafeWorkspaceService()
    session = service.create_import(str(source))
    service.run_import(session["session_id"])
    service.scan(session["session_id"])
    planner = OrganizationPlanner()
    planner.plan(session["session_id"])

    plan_path = workspace / "imports" / session["session_id"] / "organization_plan.json"
    plan = json.loads(plan_path.read_text(encoding="utf-8"))
    proposal = next(p for p in plan["proposals"] if p["action"] == "suggest_move")
    proposal["target_folder"] = f"{settings.FINAL_ROOT.name}/../../Outside"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")

    result = planner.apply(session["session_id"], [proposal["relative_path"]])
    assert result["results"][0]["status"] == "failed"
    assert not (workspace.parent / "Outside").exists()


def test_organization_apply_conflict_does_not_overwrite(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    final = workspace / "Final"
    workspace.mkdir()
    source.mkdir()
    source_file = source / "invoice.txt"
    source_file.write_text("Invoice ABC 2025\nPayment due", encoding="utf-8")
    original = source_file.read_bytes()

    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "FINAL_ROOT", final)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    workspace_service = SafeWorkspaceService()
    created = workspace_service.create_import()
    workspace_service.run_import(created["session_id"])
    workspace_service.scan(created["session_id"])
    planner = OrganizationPlanner()
    plan = planner.plan(created["session_id"])

    proposal = next(p for p in plan["proposals"] if p["action"] == "suggest_move")
    target = final / Path(proposal["target_folder"]).relative_to(final.name) / proposal["suggested_filename"]
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("pre-existing different content", encoding="utf-8")

    result = planner.apply(created["session_id"], [proposal["relative_path"]])
    assert result["results"][0]["status"] == "conflict"
    assert target.read_text(encoding="utf-8") == "pre-existing different content"
    assert source_file.read_bytes() == original


def test_organization_category_uses_document_content(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    final = workspace / "Final"
    workspace.mkdir()
    source.mkdir()
    (source / "2025_001.txt").write_text(
        "COMMERCIAL INVOICE\nInvoice Number: 001\nPayment due date: 2025-12-31",
        encoding="utf-8",
    )

    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "FINAL_ROOT", final)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    workspace_service = SafeWorkspaceService()
    created = workspace_service.create_import()
    workspace_service.run_import(created["session_id"])
    workspace_service.scan(created["session_id"])
    workspace_service._write(
        workspace_service._json_path(created["session_id"], "understanding.json"),
        {"results": [{"relative_path": "2025_001.txt", "text_preview": "ordinary document text"}]},
    )
    workspace_service._write(
        workspace_service._json_path(created["session_id"], "ocr_corrections.json"),
        {"results": {"2025_001.txt": "Commercial invoice. Invoice Number: 001. Payment due date: 2025-12-31"}},
    )
    planner = OrganizationPlanner()
    plan = planner.plan(created["session_id"])
    proposal = plan["proposals"][0]
    assert proposal["category"] == "Invoices"
    assert "Invoices" in proposal["target_folder"]



def test_apply_rejects_plan_after_inventory_or_ocr_changes(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    workspace.mkdir()
    source.mkdir()
    (source / "invoice.txt").write_text("Invoice 001 payment", encoding="utf-8")

    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "FINAL_ROOT", workspace / "Final")
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    service = SafeWorkspaceService()
    created = service.create_import()
    service.run_import(created["session_id"])
    service.scan(created["session_id"])
    planner = OrganizationPlanner()
    plan = planner.plan(created["session_id"])
    approved = [item["relative_path"] for item in plan["proposals"]]

    service._write(
        service._json_path(created["session_id"], "understanding.json"),
        {"results": [{"relative_path": "invoice.txt", "text_preview": "updated OCR content"}]},
    )

    import pytest
    with pytest.raises(ValueError, match="plan is stale"):
        planner.apply(created["session_id"], approved)
    assert not (workspace / "Final").exists()



def test_apply_rejects_oversized_and_duplicate_approval_batches():
    planner = OrganizationPlanner()
    with pytest.raises(ValueError, match="At most 500"):
        planner.apply("session", [f"file-{index}.txt" for index in range(501)])
    with pytest.raises(ValueError, match="Duplicate approved paths"):
        planner.apply("session", ["invoice.txt", "invoice.txt"])

def test_apply_rejects_final_root_that_points_at_original_source(tmp_path, monkeypatch):
    workspace = tmp_path / "workspace"
    source = tmp_path / "source"
    workspace.mkdir()
    source.mkdir()
    source_file = source / "invoice.txt"
    source_file.write_text("Invoice 001 payment", encoding="utf-8")
    original = source_file.read_bytes()

    monkeypatch.setattr(settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(settings, "SOURCE_ROOT", source)
    monkeypatch.setattr(settings, "FINAL_ROOT", source)
    monkeypatch.setattr(settings, "ORIGINAL_READ_ONLY", True)
    monkeypatch.setattr(settings, "ALLOW_SOURCE_WRITE", False)

    service = SafeWorkspaceService()
    created = service.create_import()
    service.run_import(created["session_id"])
    service.scan(created["session_id"])
    planner = OrganizationPlanner()
    plan = planner.plan(created["session_id"])
    approved = [item["relative_path"] for item in plan["proposals"] if item["action"] == "suggest_move"]

    with pytest.raises(ValueError, match="FINAL_ROOT"):
        planner.apply(created["session_id"], approved)

    assert source_file.read_bytes() == original
    assert list(source.iterdir()) == [source_file]
