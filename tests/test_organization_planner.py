from app.services.organization_planner import normalize_stem


def test_normalize_stem_groups_common_versions():
    base = normalize_stem("Invoice ABC 2025.pdf")
    assert base == normalize_stem("Invoice ABC 2025 copy.pdf")
    assert base == normalize_stem("Invoice ABC 2025 v2.pdf")
    assert base == normalize_stem("Invoice ABC 2025 final.pdf")


def test_normalize_stem_keeps_different_documents_separate():
    assert normalize_stem("Invoice ABC.pdf") != normalize_stem("Invoice XYZ.pdf")
