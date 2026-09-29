from app.services.organization_planner import OrganizationPlanner, normalize_stem
from app.core.config import settings


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
