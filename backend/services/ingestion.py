import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pandas as pd
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.models.complaint import Complaint
from backend.models.job import IngestionJob
from ml.engine import predict

logger = logging.getLogger(__name__)

REQUIRED_COLUMNS = {"text", "created_at", "resolved_at"}
PROGRESS_COMMIT_EVERY = 5


def should_flag_for_review(
    confidence: float,
    alternatives: list | None = None,
) -> bool:
    """Flag for human review when the model is soft and not a clear winner.

    4-class max-probability is often ~0.3-0.5 even for correct predictions.
    If top-1 beats top-2 by CONFIDENCE_MARGIN, trust the label automatically.
    """
    conf = float(confidence)
    alts = alternatives or []
    if not alts:
        return conf < settings.confidence_threshold
    second = float(alts[0].get("confidence") or 0.0)
    margin = conf - second
    if margin >= settings.confidence_margin:
        return False
    return conf < settings.confidence_threshold


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _mark_job(
    db: Session,
    job: IngestionJob,
    *,
    status: str | None = None,
    error_message: str | None = None,
    total_rows: int | None = None,
    processed_rows: int | None = None,
    skipped_rows: int | None = None,
    error_rows: int | None = None,
    quality_summary: str | None = None,
) -> None:
    if status is not None:
        job.status = status
    if error_message is not None:
        job.error_message = error_message
    if total_rows is not None:
        job.total_rows = total_rows
    if processed_rows is not None:
        job.processed_rows = processed_rows
    if skipped_rows is not None:
        job.skipped_rows = skipped_rows
    if error_rows is not None:
        job.error_rows = error_rows
    if quality_summary is not None:
        job.quality_summary = quality_summary
    if status == "processing" and job.started_at is None:
        job.started_at = _utcnow()
    if status in {"completed", "failed"}:
        job.completed_at = _utcnow()
    db.commit()


def _read_csv(file_path: str) -> pd.DataFrame:
    """Read CSV with encoding fallbacks. Raises ValueError with a clear message."""
    last_error: Exception | None = None
    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            return pd.read_csv(file_path, encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
            continue
        except pd.errors.EmptyDataError as exc:
            raise ValueError("CSV contains no data rows") from exc
        except pd.errors.ParserError as exc:
            raise ValueError(f"Malformed CSV: {exc}") from exc
    raise ValueError(f"Could not decode CSV (tried utf-8-sig, utf-8, latin-1): {last_error}")


def process_csv(file_path: str, job_id: str) -> None:
    db = SessionLocal()
    job = db.get(IngestionJob, job_id)

    if job is None:
        logger.error("Ingestion job %s not found", job_id)
        db.close()
        return

    quality = {
        "missing_text": 0,
        "invalid_timestamps": 0,
        "duplicate_rows": 0,
        "prediction_errors": 0,
        "unexpected_columns": [],
    }

    try:
        _mark_job(db, job, status="processing")

        try:
            df = _read_csv(file_path)
        except ValueError as exc:
            _mark_job(db, job, status="failed", error_message=str(exc), total_rows=0)
            return

        unexpected = sorted(set(df.columns) - REQUIRED_COLUMNS - {"category"})
        quality["unexpected_columns"] = unexpected

        if not REQUIRED_COLUMNS.issubset(df.columns):
            missing = sorted(REQUIRED_COLUMNS - set(df.columns))
            _mark_job(
                db,
                job,
                status="failed",
                error_message=(
                    "CSV is missing required columns: "
                    + ", ".join(missing)
                    + ". Expected columns: text, created_at, resolved_at."
                ),
                total_rows=int(len(df)),
                quality_summary=json.dumps(quality),
            )
            return

        if df.empty:
            _mark_job(
                db,
                job,
                status="failed",
                error_message="CSV contains no data rows",
                total_rows=0,
                quality_summary=json.dumps(quality),
            )
            return

        total_rows = len(df)
        processed = 0
        skipped = 0
        errors = 0
        seen: set[tuple[str, str]] = set()

        _mark_job(db, job, status="processing", total_rows=total_rows)
        logger.info("Job %s processing %s records", job_id, total_rows)

        # Fail fast if model cannot load at all
        try:
            predict("health check probe")
        except Exception as exc:
            logger.exception("Job %s model unavailable", job_id)
            _mark_job(
                db,
                job,
                status="failed",
                error_message=(
                    "ML model is unavailable. Train the model with "
                    f"`python -m ml.train` before uploading. Detail: {exc}"
                ),
                total_rows=total_rows,
                quality_summary=json.dumps(quality),
            )
            return

        for _, row in df.iterrows():
            text = str(row["text"]).strip() if pd.notna(row["text"]) else ""
            if not text:
                skipped += 1
                quality["missing_text"] += 1
                continue

            created_at = pd.to_datetime(row["created_at"], errors="coerce")
            if pd.isna(created_at):
                skipped += 1
                quality["invalid_timestamps"] += 1
                continue
            created_at_dt = created_at.to_pydatetime()
            created_key = created_at_dt.isoformat(sep=" ", timespec="seconds")

            dup_key = (text.casefold(), created_key)
            if dup_key in seen:
                skipped += 1
                quality["duplicate_rows"] += 1
                continue
            seen.add(dup_key)

            resolved_at = None
            if pd.notna(row["resolved_at"]) and str(row["resolved_at"]).strip():
                parsed = pd.to_datetime(row["resolved_at"], errors="coerce")
                if pd.isna(parsed):
                    skipped += 1
                    quality["invalid_timestamps"] += 1
                    continue
                resolved_at = parsed.to_pydatetime()
                if resolved_at < created_at_dt:
                    # Keep row but treat inverted timestamps as data-quality skip of resolved_at
                    resolved_at = None
                    quality["invalid_timestamps"] += 1

            try:
                prediction = predict(text)
                confidence = float(prediction["confidence"])
                category = prediction["category"]
                needs_review = should_flag_for_review(
                    confidence, prediction.get("alternatives")
                )
            except Exception as exc:
                logger.warning("Job %s row prediction failed: %s", job_id, exc)
                errors += 1
                quality["prediction_errors"] += 1
                # Persist progress so the UI can show error_rows rising
                if (processed + skipped + errors) % PROGRESS_COMMIT_EVERY == 0:
                    _mark_job(
                        db,
                        job,
                        processed_rows=processed,
                        skipped_rows=skipped,
                        error_rows=errors,
                    )
                continue

            db.add(
                Complaint(
                    text=text,
                    category=category,
                    confidence=confidence,
                    needs_review=needs_review,
                    job_id=job_id,
                    created_at=created_at_dt,
                    resolved_at=resolved_at,
                )
            )
            processed += 1

            accounted = processed + skipped + errors
            if accounted % PROGRESS_COMMIT_EVERY == 0 or accounted == total_rows:
                db.commit()
                _mark_job(
                    db,
                    job,
                    processed_rows=processed,
                    skipped_rows=skipped,
                    error_rows=errors,
                )

        db.commit()
        summary = json.dumps(quality)
        if processed == 0 and errors > 0:
            _mark_job(
                db,
                job,
                status="failed",
                error_message=(
                    f"No complaints stored. {errors} prediction error(s), "
                    f"{skipped} skipped. Check model availability and CSV quality."
                ),
                total_rows=total_rows,
                processed_rows=processed,
                skipped_rows=skipped,
                error_rows=errors,
                quality_summary=summary,
            )
        else:
            _mark_job(
                db,
                job,
                status="completed",
                total_rows=total_rows,
                processed_rows=processed,
                skipped_rows=skipped,
                error_rows=errors,
                quality_summary=summary,
                error_message=None,
            )
            logger.info(
                "Job %s completed: processed=%s skipped=%s errors=%s",
                job_id,
                processed,
                skipped,
                errors,
            )

    except Exception as exc:
        logger.exception("Job %s failed: %s", job_id, exc)
        db.rollback()
        job = db.get(IngestionJob, job_id)
        if job is not None:
            _mark_job(
                db,
                job,
                status="failed",
                error_message=f"Ingestion failed unexpectedly: {exc}",
                quality_summary=json.dumps(quality),
            )
    finally:
        db.close()


def classify_text(text: str) -> dict:
    prediction = predict(text)
    confidence = float(prediction["confidence"])
    alternatives = prediction.get("alternatives", [])
    needs_review = should_flag_for_review(confidence, alternatives)
    return {
        "category": prediction["category"],
        "confidence": confidence,
        "needs_review": needs_review,
        "model_version": prediction.get("model_version", "unknown"),
        "alternatives": alternatives,
    }


def safe_upload_path(filename: str) -> Path:
    upload_root = Path(settings.upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).name or "upload.csv"
    return upload_root / f"{uuid4().hex}_{safe_name}"
