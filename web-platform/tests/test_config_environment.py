from app.core.config import default_debug_for_environment, normalize_environment


def test_prod_alias_is_normalized_before_security_validation():
    assert normalize_environment("prod") == "production"
    assert normalize_environment(" PRODUCTION ") == "production"


def test_debug_defaults_off_for_production_alias_and_staging():
    normalized_prod = normalize_environment("prod")
    assert default_debug_for_environment(normalized_prod) is False
    assert default_debug_for_environment("production") is False
    assert default_debug_for_environment("staging") is False


def test_debug_defaults_on_for_local_development():
    assert default_debug_for_environment("development") is True
    assert default_debug_for_environment("local") is True
