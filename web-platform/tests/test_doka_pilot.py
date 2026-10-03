from pathlib import Path
import importlib.util
import json

from app.core import config as config_module


def _load_pilot_module():
    path = Path(__file__).resolve().parents[2] / "scripts" / "doka_pilot_check.py"
    spec = importlib.util.spec_from_file_location("doka_pilot_check", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_doka_pilot_gate_preserves_source_and_creates_reproducible_report(tmp_path, monkeypatch, capsys):
    source = tmp_path / "office-copy"
    source.mkdir()
    (source / "invoice.txt").write_text("Commercial Invoice 2025\nSupplier: Demo Logistics", encoding="utf-8")
    before = (source / "invoice.txt").read_bytes()

    workspace = tmp_path / "workspace"
    backups = tmp_path / "backups"
    final = workspace / "Final"
    quarantine = workspace / "Quarantine"
    monkeypatch.setattr(config_module.settings, "WORKING_ROOT", workspace)
    monkeypatch.setattr(config_module.settings, "BACKUP_ROOT", backups)
    monkeypatch.setattr(config_module.settings, "FINAL_ROOT", final)
    monkeypatch.setattr(config_module.settings, "QUARANTINE_ROOT", quarantine)

    module = _load_pilot_module()
    monkeypatch.setattr(
        __import__("sys"),
        "argv",
        ["doka_pilot_check.py", "--source", str(source)],
    )

    assert module.main() == 0
    report = json.loads(capsys.readouterr().out)

    assert report["gate"] == "passed"
    assert report["source_unchanged"] is True
    assert report["import"]["files_verified"] == 1
    assert report["scan"]["files_total"] == 1
    assert report["understanding"]["analyzed_files"] == 1
    assert report["organization_plan"]["requires_user_approval"] is True
    assert report["backup"]["sha256"]
    assert report["backup"]["verified"] is True
    assert report["backup"]["recovery_verified"] is True
    assert report["backup"]["recovery_active_workspace_changed"] is False
    assert (source / "invoice.txt").read_bytes() == before



def test_workspace_backup_snapshot_matches_backup_exclusions(tmp_path):
    module = _load_pilot_module()
    (tmp_path / "imports").mkdir()
    (tmp_path / "imports" / "status.json").write_text("{}", encoding="utf-8")
    (tmp_path / "Recovery" / "restore_old").mkdir(parents=True)
    (tmp_path / "Recovery" / "restore_old" / "old.txt").write_text("old", encoding="utf-8")
    (tmp_path / "temporary.tmp").write_text("partial", encoding="utf-8")
    (tmp_path / "keep.txt").write_text("keep", encoding="utf-8")

    snapshot = module.workspace_backup_snapshot(tmp_path)
    assert set(snapshot) == {"imports/status.json", "keep.txt"}


def test_ocr_pilot_requires_real_myanmar_and_english_samples():
    module = _load_pilot_module()
    report = module.inspect_ocr_results([
        {"relative_path": "myanmar.png", "extension": ".png", "text_length": 40, "language": "mya"},
        {"relative_path": "english.pdf", "extension": ".pdf", "text_length": 55, "language": "eng"},
    ])
    assert report["representative_ocr_passed"] is True
    assert report["myanmar_detected"] is True
    assert report["english_detected"] is True

    incomplete = module.inspect_ocr_results([
        {"relative_path": "myanmar.png", "extension": ".png", "text_length": 40, "language": "mya"},
    ])
    assert incomplete["representative_ocr_passed"] is False



def test_doka_pilot_rejects_empty_source_copy(tmp_path, monkeypatch, capsys):
    source = tmp_path / "empty-copy"
    source.mkdir()
    module = _load_pilot_module()
    monkeypatch.setattr(
        __import__("sys"),
        "argv",
        ["doka_pilot_check.py", "--source", str(source)],
    )

    assert module.main() == 2
    report = json.loads(capsys.readouterr().out)
    assert report["gate"] == "blocked"
    assert "no regular files" in report["reason"]
