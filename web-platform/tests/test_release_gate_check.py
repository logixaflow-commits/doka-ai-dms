from __future__ import annotations

from scripts.release_gate_check import gate_ready


def _all_prerequisites():
    return {
        1: {"passed": True},
        2: {"passed": True},
        3: {"gate_ready": True},
        4: {"passed": True},
        5: {"source_unchanged": True, "recovery_verified": True},
        6: {"recovery_verified": True, "rto_seconds": 12.5},
        7: {"passed": True},
        8: {"passed": True},
        9: {"gate9_ready": True, "checks": {"two_user_isolation": True}},
        10: {"checks": {"two_user_isolation": True}},
        11: {"checks": {
            "supabase_storage": True,
            "b2_recovery": True,
            "cloudinary_application_path": True,
            "google_drive_recovery": True,
            "exact_50_mib_boundary": True,
        }},
    }


def test_gate_12_requires_explicit_final_signoff():
    evidence = _all_prerequisites()
    assert not gate_ready(12, evidence)
    evidence[12] = {"passed": True}
    assert gate_ready(12, evidence)


def test_gate_12_stays_pending_if_any_cloud_gate_is_missing():
    evidence = _all_prerequisites()
    evidence[12] = {"passed": True}
    evidence[11]["checks"]["b2_recovery"] = False
    assert not gate_ready(12, evidence)
