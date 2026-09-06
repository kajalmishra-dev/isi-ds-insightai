import pytest


def test_settings_load_defaults(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.delenv("API_KEY", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("REQUIRE_AUTH_IN_PRODUCTION", "false")
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0.6")

    from backend.core.config import Settings

    settings = Settings()
    assert settings.auth_enabled is False
    assert settings.app_name == "InsightAI"
    assert 0.0 <= settings.confidence_threshold <= 1.0


def test_auth_enabled_requires_api_key(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEY", "")
    monkeypatch.setenv("ENVIRONMENT", "development")

    from backend.core.config import Settings

    with pytest.raises(ValueError, match="API_KEY"):
        Settings()


def test_require_auth_in_production_default(monkeypatch):
    """Production/staging require auth by default (REQUIRE_AUTH_IN_PRODUCTION=true)."""
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.delenv("REQUIRE_AUTH_IN_PRODUCTION", raising=False)
    monkeypatch.delenv("API_KEY", raising=False)

    from backend.core.config import Settings

    with pytest.raises(ValueError, match="AUTH_ENABLED"):
        Settings()


def test_require_auth_in_production_can_opt_out(monkeypatch):
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("REQUIRE_AUTH_IN_PRODUCTION", "false")
    monkeypatch.delenv("API_KEY", raising=False)

    from backend.core.config import Settings

    settings = Settings()
    assert settings.auth_enabled is False


def test_cors_origins_wildcard(monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("CORS_ORIGINS", "*")

    from backend.core.config import Settings

    settings = Settings()
    assert settings.cors_origins == ["*"]
