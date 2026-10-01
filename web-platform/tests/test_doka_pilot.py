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
    assert (source / "invoice.txt").read_bytes() == before
