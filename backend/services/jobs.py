"""Ingestion job lifecycle helpers."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.models.job import IngestionJob

logger = logging.getLogger(__name__)

STUCK_MESSAGE = (
    "Job was interrupted while processing (application restart or worker loss). "
    "Use POST /api/v1/jobs/{id}/retry if the source file is still available."
)


def reclaim_stuck_jobs(db: Session) -> int:
    """Mark abandoned `processing` jobs as failed after a process restart.

    FastAPI BackgroundTasks die with the process, so jobs left in `processing`
    cannot complete. Reclaiming them keeps the job API honest.
    """
    stuck = (
        db.query(IngestionJob)
        .filter(IngestionJob.status == "processing")
        .all()
    )
    if not stuck:
        return 0

    now = datetime.now(timezone.utc)
    for job in stuck:
        job.status = "failed"
        job.error_message = STUCK_MESSAGE
        job.completed_at = now
        logger.warning("Reclaimed stuck job %s (was processing)", job.id)

    db.commit()
    return len(stuck)
