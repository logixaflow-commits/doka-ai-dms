from app.services.organization_planner import normalize_stem


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
