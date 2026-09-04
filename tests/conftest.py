import importlib
import os

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'test.db'}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))
    monkeypatch.setenv("TESTING", "1")
    monkeypatch.setenv("AUTH_ENABLED", "false")
    monkeypatch.setenv("REQUIRE_AUTH_IN_PRODUCTION", "false")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.delenv("API_KEY", raising=False)

    import backend.core.config as config_module
    import backend.core.database as database_module
    import backend.core.deps as deps_module
    import backend.core.schema as schema_module
    import backend.core.security as security_module
    import backend.services.ingestion as ingestion_module
    import backend.services.analytics as analytics_module
    import backend.api.routes as routes_module
    import backend.main as main_module

    config_module.get_settings.cache_clear()
    importlib.reload(config_module)
    importlib.reload(database_module)
    importlib.reload(deps_module)
    importlib.reload(schema_module)
    importlib.reload(security_module)
    importlib.reload(ingestion_module)
    importlib.reload(analytics_module)
    importlib.reload(routes_module)
    importlib.reload(main_module)

    with TestClient(main_module.app) as test_client:
        yield test_client
