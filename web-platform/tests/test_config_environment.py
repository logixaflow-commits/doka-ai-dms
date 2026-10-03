from app.core.config import default_debug_for_environment, normalize_environment, validate_runtime_mode


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


def test_explicit_debug_mode_is_rejected_in_production():
    import pytest

    with pytest.raises(ValueError, match="DEBUG must be false in production"):
        validate_runtime_mode("production", True)


def test_debug_mode_remains_available_outside_production():
    validate_runtime_mode("staging", True)
    validate_runtime_mode("development", True)
