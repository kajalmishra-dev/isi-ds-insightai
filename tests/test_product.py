def _upload_csv(client, monkeypatch, csv_content: str, filename: str = "data.csv"):
    monkeypatch.setattr(
        "backend.services.ingestion.predict",
        lambda text: (
            {"category": "technical", "confidence": 0.9}
            if text == "health check probe"
            else {"category": "billing", "confidence": 0.88}
        ),
    )
    return client.post(
        "/api/v1/upload",
        files={"file": (filename, csv_content, "text/csv")},
    )


CSV_OK = (
    "text,created_at,resolved_at\n"
    '"Invoice is wrong",2026-01-01 09:00:00,2026-01-01 12:00:00\n'
)


def test_upload_idempotent_for_identical_content(client, monkeypatch):
    first = _upload_csv(client, monkeypatch, CSV_OK)
    assert first.status_code == 202
    first_body = first.json()
    assert first_body["deduplicated"] is False

    second = _upload_csv(client, monkeypatch, CSV_OK)
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["deduplicated"] is True
    assert second_body["job_id"] == first_body["job_id"]

    complaints = client.get("/api/v1/complaints").json()
    assert complaints["total"] == 1


def test_export_job_and_complaints_csv(client, monkeypatch):
    job_id = _upload_csv(client, monkeypatch, CSV_OK).json()["job_id"]

    job_csv = client.get(f"/api/v1/jobs/{job_id}/export.csv")
    assert job_csv.status_code == 200
    assert "text/csv" in job_csv.headers.get("content-type", "")
    body = job_csv.text
    assert "Invoice is wrong" in body
    assert "billing" in body

    all_csv = client.get("/api/v1/complaints/export.csv")
    assert all_csv.status_code == 200
    assert "Invoice is wrong" in all_csv.text


def test_retry_failed_job(client, monkeypatch, tmp_path):
    calls = {"n": 0}

    def flaky(text):
        if text == "health check probe":
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("model offline")
            return {"category": "technical", "confidence": 0.9}
        return {"category": "service", "confidence": 0.9}

    monkeypatch.setattr("backend.services.ingestion.predict", flaky)
    upload = client.post(
        "/api/v1/upload",
        files={"file": ("retry.csv", CSV_OK, "text/csv")},
    )
    job_id = upload.json()["job_id"]
    failed = client.get(f"/api/v1/jobs/{job_id}").json()
    assert failed["status"] == "failed"

    retry = client.post(f"/api/v1/jobs/{job_id}/retry")
    assert retry.status_code == 202
    assert retry.json()["job_id"] == job_id

    completed = client.get(f"/api/v1/jobs/{job_id}").json()
    assert completed["status"] == "completed"
    assert completed["processed_rows"] == 1


def test_retry_rejects_non_failed_job(client, monkeypatch):
    job_id = _upload_csv(client, monkeypatch, CSV_OK).json()["job_id"]
    response = client.post(f"/api/v1/jobs/{job_id}/retry")
    assert response.status_code == 400
