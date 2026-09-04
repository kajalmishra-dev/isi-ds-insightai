import hashlib
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import JSONResponse, Response
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.deps import get_db
from backend.core.security import require_api_key
from backend.models.complaint import Complaint
from backend.models.job import IngestionJob
from backend.schemas.complaint import (
    AnalyticsSummary,
    ComplaintListResponse,
    ComplaintResponse,
    JobResponse,
    PredictRequest,
    PredictResponse,
    ReviewDecision,
    UploadAccepted,
)
from backend.services.analytics import SORTABLE_COLUMNS, get_summary, list_complaints
from backend.services.export import export_filtered_complaints, export_job_complaints
from backend.services.ingestion import classify_text, process_csv, safe_upload_path

router = APIRouter(dependencies=[Depends(require_api_key)])
logger = logging.getLogger(__name__)

ACTIVE_STATUSES = ("pending", "processing", "completed")


def _schedule_ingest(background_tasks: BackgroundTasks, file_path: str, job_id: str) -> None:
    if os.getenv("TESTING") == "1":
        process_csv(file_path, job_id)
    else:
        background_tasks.add_task(process_csv, file_path, job_id)


def _to_job_response(job: IngestionJob) -> JobResponse:
    """Serialize job without leaking server filesystem paths."""
    payload = JobResponse.model_validate(job)
    can_retry = (
        job.status == "failed"
        and bool(job.source_path)
        and Path(job.source_path).exists()
    )
    return payload.model_copy(update={"can_retry": can_retry})


def _dedupe_payload(job: IngestionJob) -> JSONResponse:
    payload = UploadAccepted(
        job_id=job.id,
        message=(
            "Identical file content was already accepted. "
            "Returning the existing job instead of reprocessing."
        ),
        status=job.status,
        deduplicated=True,
    )
    return JSONResponse(status_code=status.HTTP_200_OK, content=payload.model_dump())


@router.post(
    "/upload",
    response_model=UploadAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Upload complaint CSV for async classification",
)
def upload_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only .csv files are accepted",
        )

    raw = file.file.read(settings.max_upload_bytes + 1)
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds max size of {settings.max_upload_bytes} bytes",
        )
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty",
        )

    content_hash = hashlib.sha256(raw).hexdigest()
    existing = (
        db.query(IngestionJob)
        .filter(
            IngestionJob.content_hash == content_hash,
            IngestionJob.status.in_(ACTIVE_STATUSES),
        )
        .order_by(IngestionJob.created_at.desc())
        .first()
    )
    if existing is not None:
        return _dedupe_payload(existing)

    destination = safe_upload_path(file.filename)
    destination.write_bytes(raw)

    job_id = str(uuid4())
    job = IngestionJob(
        id=job_id,
        filename=file.filename,
        status="pending",
        content_hash=content_hash,
        source_path=str(destination),
        created_at=datetime.now(timezone.utc),
    )
    db.add(job)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raced = (
            db.query(IngestionJob)
            .filter(
                IngestionJob.content_hash == content_hash,
                IngestionJob.status.in_(ACTIVE_STATUSES),
            )
            .order_by(IngestionJob.created_at.desc())
            .first()
        )
        if raced is not None:
            try:
                destination.unlink(missing_ok=True)
            except OSError:
                pass
            return _dedupe_payload(raced)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Could not create ingestion job due to a concurrent upload conflict.",
        )

    _schedule_ingest(background_tasks, str(destination), job_id)

    return UploadAccepted(
        job_id=job_id,
        message="File accepted. Classification running in background.",
        status="pending",
        deduplicated=False,
    )


@router.get("/jobs/{job_id}", response_model=JobResponse, summary="Get ingestion job status")
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return _to_job_response(job)


@router.get(
    "/jobs",
    response_model=list[JobResponse],
    summary="List recent ingestion jobs",
)
def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    jobs = (
        db.query(IngestionJob)
        .order_by(IngestionJob.created_at.desc())
        .limit(limit)
        .all()
    )
    return [_to_job_response(job) for job in jobs]


@router.post(
    "/jobs/{job_id}/retry",
    response_model=UploadAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Retry a failed ingestion job",
)
def retry_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if job.status != "failed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Only failed jobs can be retried (current status: {job.status})",
        )
    if not job.source_path or not Path(job.source_path).exists():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Original upload file is no longer available on disk. "
                "Please upload the CSV again."
            ),
        )

    db.query(Complaint).filter(Complaint.job_id == job_id).delete()
    job.status = "pending"
    job.error_message = None
    job.quality_summary = None
    job.total_rows = 0
    job.processed_rows = 0
    job.skipped_rows = 0
    job.error_rows = 0
    job.started_at = None
    job.completed_at = None
    db.commit()

    _schedule_ingest(background_tasks, job.source_path, job_id)
    logger.info("Retry scheduled for job %s", job_id)

    return UploadAccepted(
        job_id=job_id,
        message="Failed job queued for retry.",
        status="pending",
        deduplicated=False,
    )


@router.get(
    "/jobs/{job_id}/export.csv",
    summary="Download classified complaints for a job as CSV",
)
def export_job_csv(job_id: str, db: Session = Depends(get_db)):
    job = db.get(IngestionJob, job_id)
    if job is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    csv_text = export_job_complaints(db, job_id)
    filename = f"insightai_job_{job_id[:8]}.csv"
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get(
    "/complaints/export.csv",
    summary="Download filtered complaints as CSV",
)
def export_complaints_csv(
    category: str | None = Query(None),
    search: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    needs_review: bool | None = Query(None),
    min_confidence: float | None = Query(None, ge=0.0, le=1.0),
    max_confidence: float | None = Query(None, ge=0.0, le=1.0),
    limit: int = Query(5000, ge=1, le=20000),
    db: Session = Depends(get_db),
):
    csv_text = export_filtered_complaints(
        db,
        category=category,
        search=search,
        date_from=date_from,
        date_to=date_to,
        needs_review=needs_review,
        min_confidence=min_confidence,
        max_confidence=max_confidence,
        limit=limit,
    )
    return Response(
        content=csv_text,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="insightai_complaints.csv"'},
    )


@router.get(
    "/analytics/summary",
    response_model=AnalyticsSummary,
    summary="Aggregated complaint intelligence metrics",
)
def analytics_summary(db: Session = Depends(get_db)):
    try:
        return get_summary(db)
    except Exception as exc:
        logger.exception("Analytics endpoint failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Analytics computation failed. Check server logs for details.",
        ) from exc


@router.get(
    "/complaints",
    response_model=ComplaintListResponse,
    summary="Paginated complaints with search, sort, and filters",
)
def get_complaints(
    page: int = Query(1, ge=1),
    page_size: int | None = Query(None, ge=1),
    category: str | None = Query(None),
    search: str | None = Query(None, description="Case-insensitive substring match on text"),
    sort_by: str = Query("id", description=f"One of: {', '.join(SORTABLE_COLUMNS)}"),
    sort_order: str = Query("desc"),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    needs_review: bool | None = Query(None),
    min_confidence: float | None = Query(None, ge=0.0, le=1.0),
    max_confidence: float | None = Query(None, ge=0.0, le=1.0),
    db: Session = Depends(get_db),
):
    if sort_by not in SORTABLE_COLUMNS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid sort_by. Allowed: {', '.join(sorted(SORTABLE_COLUMNS))}",
        )
    if sort_order.lower() not in {"asc", "desc"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="sort_order must be 'asc' or 'desc'",
        )
    if date_from and date_to and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="date_from cannot be after date_to",
        )
    if (
        min_confidence is not None
        and max_confidence is not None
        and min_confidence > max_confidence
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="min_confidence cannot be greater than max_confidence",
        )

    size = page_size or settings.default_page_size
    size = min(size, settings.max_page_size)

    items, total, total_pages = list_complaints(
        db,
        page=page,
        page_size=size,
        category=category,
        search=search,
        date_from=date_from,
        date_to=date_to,
        needs_review=needs_review,
        min_confidence=min_confidence,
        max_confidence=max_confidence,
        sort_by=sort_by,
        sort_order=sort_order,
    )

    return ComplaintListResponse(
        items=items,
        total=total,
        page=page,
        page_size=size,
        total_pages=total_pages,
    )


@router.post(
    "/complaints/{complaint_id}/review",
    response_model=ComplaintResponse,
    summary="Approve or reclassify a complaint (clears needs_review)",
)
def review_complaint(
    complaint_id: int,
    payload: ReviewDecision,
    db: Session = Depends(get_db),
):
    row = db.get(Complaint, complaint_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Complaint not found")

    category = payload.category.strip().lower().replace(" ", "_")
    if not category or category == "needs_review":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Provide a real category label (not needs_review).",
        )

    row.category = category
    row.needs_review = False
    db.commit()
    db.refresh(row)
    return row


@router.post(
    "/predict",
    response_model=PredictResponse,
    summary="Classify a single complaint text",
)
def predict_endpoint(payload: PredictRequest):
    try:
        result = classify_text(payload.text)
    except Exception as exc:
        logger.exception("Prediction failed")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Model unavailable. Try again after training/loading the model.",
        ) from exc
    return PredictResponse(**result)
