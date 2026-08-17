def test_health(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_analytics_empty(client):
    response = client.get("/analytics/summary")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_complaints"] == 0
    assert payload["north_star_metric"] == 0


def test_upload_and_complaints(client, monkeypatch):
    def fake_predict(text):
        return {"category": "technical", "confidence": 0.91}

    monkeypatch.setattr("backend.api.routes.predict", fake_predict)

    csv_content = (
        "text,created_at,resolved_at\n"
        '"App crash on login",2026-01-01 09:00:00,2026-01-01 12:00:00\n'
    )
    response = client.post(
        "/upload",
        files={"file": ("complaints.csv", csv_content, "text/csv")},
    )
    assert response.status_code == 200

    complaints = client.get("/complaints").json()
    assert len(complaints) == 1
    assert complaints[0]["category"] == "technical"

    summary = client.get("/analytics/summary").json()
    assert summary["total_complaints"] == 1


def test_low_confidence_routes_to_review(client, monkeypatch):
    monkeypatch.setattr(
        "backend.api.routes.predict",
        lambda _text: {"category": "billing", "confidence": 0.2},
    )

    csv_content = (
        "text,created_at,resolved_at\n"
        '"Unclear charge",2026-01-01 09:00:00,2026-01-01 12:00:00\n'
    )
    client.post(
        "/upload",
        files={"file": ("complaints.csv", csv_content, "text/csv")},
    )

    complaints = client.get("/complaints").json()
    assert complaints[0]["category"] == "needs_review"
