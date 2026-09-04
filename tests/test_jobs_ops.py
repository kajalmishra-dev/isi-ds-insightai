from datetime import datetime, timezone
from pathlib import Path

from backend.models.job import IngestionJob
from backend.services.jobs import reclaim_stuck_jobs


def test_reclaim_stuck_processing_jobs(client):
    # Insert a stuck processing job directly via app DB session factory
    from backend.core.database import SessionLocal

    job_id = "stuck-job-0001"
    with SessionLocal() as db:
        db.add(
            IngestionJob(
                id=job_id,
                filename="stuck.csv",
                status="processing",
                source_path="/tmp/does-not-matter.csv",
                created_at=datetime.now(timezone.utc),
                started_at=datetime.now(timezone.utc),
            )
        )
        db.commit()

    with SessionLocal() as db:
        count = reclaim_stuck_jobs(db)
        assert count == 1
        job = db.get(IngestionJob, job_id)
        assert job.status == "failed"
        assert "interrupted" in (job.error_message or "").lower()

    body = client.get(f"/api/v1/jobs/{job_id}").json()
    assert body["status"] == "failed"
    assert "source_path" not in body
    assert body["can_retry"] is False  # path does not exist


def test_job_response_hides_source_path(client, monkeypatch):
    monkeypatch.setattr(
        "backend.services.ingestion.predict",
        lambda text: (
            {"category": "technical", "confidence": 0.9}
            if text == "health check probe"
            else {"category": "billing", "confidence": 0.9}
        ),
    )
    csv_content = (
        "text,created_at,resolved_at\n"
        '"Path should stay private",2026-01-01 09:00:00,2026-01-01 10:00:00\n'
    )
    job_id = client.post(
        "/api/v1/upload",
        files={"file": ("private.csv", csv_content, "text/csv")},
    ).json()["job_id"]

    job = client.get(f"/api/v1/jobs/{job_id}").json()
    assert "source_path" not in job
    listed = client.get("/api/v1/jobs").json()
    assert all("source_path" not in item for item in listed)

    # Internal path still exists for retry support
    from backend.core.database import SessionLocal

    with SessionLocal() as db:
        row = db.get(IngestionJob, job_id)
        assert row.source_path
        assert Path(row.source_path).exists()
        assert client.get(f"/api/v1/jobs/{job_id}").json()["can_retry"] is False
        # completed jobs are not retryable
        assert row.status == "completed"
