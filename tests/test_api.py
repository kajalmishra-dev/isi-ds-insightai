def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert "version" in body
    headers = {k.lower(): v for k, v in response.headers.items()}
    assert "x-request-id" in headers
    assert "x-response-time-ms" in headers
    float(headers["x-response-time-ms"])


def test_ready(client):
    response = client.get("/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["database"] is True
    assert "model" in body


def test_analytics_empty(client):
    response = client.get("/api/v1/analytics/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_complaints"] == 0
    assert payload["north_star_metric"] == 0
    assert payload["needs_review_count"] == 0


def test_upload_and_complaints(client, monkeypatch):
    def fake_predict(text):
        return {"category": "technical", "confidence": 0.91}

    monkeypatch.setattr("backend.services.ingestion.predict", fake_predict)

    csv_content = (
        "text,created_at,resolved_at\n"
        '"App crash on login",2026-01-01 09:00:00,2026-01-01 12:00:00\n'
    )
    response = client.post(
        "/api/v1/upload",
        files={"file": ("complaints.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 202
    job_id = response.json()["job_id"]

    job = client.get(f"/api/v1/jobs/{job_id}").json()
    assert job["status"] == "completed"
    assert job["processed_rows"] == 1
    assert job["error_rows"] == 0
    assert job["progress_percentage"] == 100.0

    complaints = client.get("/api/v1/complaints").json()
    assert complaints["total"] == 1
    assert complaints["items"][0]["category"] == "technical"
    assert complaints["items"][0]["job_id"] == job_id

    summary = client.get("/api/v1/analytics/summary").json()
    assert summary["total_complaints"] == 1
    assert summary["north_star_metric"] == 100.0


def test_low_confidence_routes_to_review(client, monkeypatch):
    monkeypatch.setattr(
        "backend.services.ingestion.predict",
        lambda _text: {"category": "billing", "confidence": 0.2},
    )

    csv_content = (
        "text,created_at,resolved_at\n"
        '"Unclear charge",2026-01-01 09:00:00,2026-01-01 12:00:00\n'
    )
    client.post(
        "/api/v1/upload",
        files={"file": ("complaints.csv", csv_content, "text/csv")},
    )

    complaints = client.get("/api/v1/complaints").json()
    item = complaints["items"][0]
    assert item["category"] == "billing"
    assert item["needs_review"] is True

    reviewed = client.post(
        f"/api/v1/complaints/{item['id']}/review",
        json={"category": "billing"},
    )
    assert reviewed.status_code == 200
    assert reviewed.json()["needs_review"] is False
    assert reviewed.json()["category"] == "billing"


def test_predict_endpoint(client, monkeypatch):
    monkeypatch.setattr(
        "backend.services.ingestion.predict",
        lambda _text: {
            "category": "shipping",
            "confidence": 0.88,
            "model_version": "tfidf-logreg-v2",
            "alternatives": [],
        },
    )
    response = client.post("/api/v1/predict", json={"text": "Package never arrived"})
    assert response.status_code == 200
    body = response.json()
    assert body["category"] == "shipping"
    assert body["needs_review"] is False
    assert body["model_version"] == "tfidf-logreg-v2"


def test_upload_rejects_non_csv(client):
    response = client.post(
        "/api/v1/upload",
        files={"file": ("notes.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 400


def test_auth_required_when_enabled(client, monkeypatch):
    monkeypatch.setenv("AUTH_ENABLED", "true")
    monkeypatch.setenv("API_KEY", "secret-key")

    import importlib

    import backend.core.config as config_module
    import backend.core.security as security_module
    import backend.api.routes as routes_module
    import backend.main as main_module

    config_module.get_settings.cache_clear()
    importlib.reload(config_module)
    importlib.reload(security_module)
    importlib.reload(routes_module)
    importlib.reload(main_module)

    from fastapi.testclient import TestClient

    with TestClient(main_module.app) as auth_client:
        denied = auth_client.get("/api/v1/analytics/summary")
        assert denied.status_code == 401

        allowed = auth_client.get(
            "/api/v1/analytics/summary",
            headers={"X-API-Key": "secret-key"},
        )
        assert allowed.status_code == 200
