import json


def _upload(client, csv_content: str, filename: str = "complaints.csv"):
    return client.post(
        "/api/v1/upload",
        files={"file": (filename, csv_content, "text/csv")},
    )


def test_job_fails_on_missing_columns(client, monkeypatch):
    monkeypatch.setattr(
        "backend.services.ingestion.predict",
        lambda _text: {"category": "technical", "confidence": 0.9},
    )
    response = _upload(client, "foo,bar\n1,2\n")
    assert response.status_code == 202
    job_id = response.json()["job_id"]
    job = client.get(f"/api/v1/jobs/{job_id}").json()
    assert job["status"] == "failed"
    assert "missing required columns" in job["error_message"].lower()


def test_job_fails_on_empty_csv(client, monkeypatch):
    monkeypatch.setattr(
        "backend.services.ingestion.predict",
        lambda _text: {"category": "technical", "confidence": 0.9},
    )
    response = _upload(client, "text,created_at,resolved_at\n")
    assert response.status_code == 202
    job = client.get(f"/api/v1/jobs/{response.json()['job_id']}").json()
    assert job["status"] == "failed"
    assert "no data" in job["error_message"].lower()


def test_skips_blank_text_invalid_dates_and_duplicates(client, monkeypatch):
    monkeypatch.setattr(
        "backend.services.ingestion.predict",
        lambda text: (
            {"category": "technical", "confidence": 0.9}
            if text == "health check probe"
            else {"category": "billing", "confidence": 0.85}
        ),
    )
    csv_content = (
        "text,created_at,resolved_at\n"
        '"",2026-01-01 09:00:00,2026-01-01 12:00:00\n'
        '"Valid complaint",not-a-date,2026-01-01 12:00:00\n'
        '"Duplicate me",2026-01-02 09:00:00,2026-01-02 12:00:00\n'
        '"Duplicate me",2026-01-02 09:00:00,2026-01-02 12:00:00\n'
        '"Unique ok",2026-01-03 09:00:00,2026-01-03 10:00:00\n'
    )
    job_id = _upload(client, csv_content).json()["job_id"]
    job = client.get(f"/api/v1/jobs/{job_id}").json()
    assert job["status"] == "completed"
    assert job["processed_rows"] == 2
    assert job["skipped_rows"] >= 3
    assert job["error_rows"] == 0
    assert job["progress_percentage"] == 100.0
    quality = json.loads(job["quality_summary"])
    assert quality["missing_text"] >= 1
    assert quality["invalid_timestamps"] >= 1
    assert quality["duplicate_rows"] >= 1


def test_row_prediction_errors_counted(client, monkeypatch):
    def fake_predict(text):
        if text == "health check probe":
            return {"category": "technical", "confidence": 0.9}
        if text == "explode":
            raise RuntimeError("model blew up")
        return {"category": "service", "confidence": 0.8}

    monkeypatch.setattr("backend.services.ingestion.predict", fake_predict)
    csv_content = (
        "text,created_at,resolved_at\n"
        '"explode",2026-01-01 09:00:00,2026-01-01 12:00:00\n'
        '"ok row",2026-01-01 10:00:00,2026-01-01 11:00:00\n'
    )
    job_id = _upload(client, csv_content).json()["job_id"]
    job = client.get(f"/api/v1/jobs/{job_id}").json()
    assert job["status"] == "completed"
    assert job["processed_rows"] == 1
    assert job["error_rows"] == 1
    quality = json.loads(job["quality_summary"])
    assert quality["prediction_errors"] == 1


def test_job_fails_when_model_unavailable(client, monkeypatch):
    def boom(_text):
        raise RuntimeError("model missing")

    monkeypatch.setattr("backend.services.ingestion.predict", boom)
    csv_content = (
        "text,created_at,resolved_at\n"
        '"Anything",2026-01-01 09:00:00,2026-01-01 12:00:00\n'
    )
    job_id = _upload(client, csv_content).json()["job_id"]
    job = client.get(f"/api/v1/jobs/{job_id}").json()
    assert job["status"] == "failed"
    assert "model" in job["error_message"].lower()


def test_predict_returns_503_when_model_raises(client, monkeypatch):
    monkeypatch.setattr(
        "backend.services.ingestion.predict",
        lambda _text: (_ for _ in ()).throw(RuntimeError("offline")),
    )
    response = client.post("/api/v1/predict", json={"text": "hello"})
    assert response.status_code == 503
    assert "detail" in response.json()
