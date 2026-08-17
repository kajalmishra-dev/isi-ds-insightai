import logging
import os
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, File, UploadFile
from sqlalchemy.orm import Session
import pandas as pd

from backend.core.config import settings
from backend.core.deps import get_db
from backend.core.database import SessionLocal
from backend.models.complaint import Complaint
from backend.services.analytics import get_summary
from ml.engine import predict

router = APIRouter()
logger = logging.getLogger(__name__)


def _safe_upload_path(filename: str) -> Path:
    upload_root = Path(settings.upload_dir)
    upload_root.mkdir(parents=True, exist_ok=True)
    safe_name = Path(filename).name
    return upload_root / f"{uuid4().hex}_{safe_name}"


def process_csv(file_path: str):
    db = SessionLocal()

    try:
        df = pd.read_csv(file_path)
        required_cols = {"text", "created_at", "resolved_at"}
        if not required_cols.issubset(df.columns):
            logger.error("CSV missing required columns")
            return

        if df.empty:
            logger.warning("CSV is empty")
            return

        logger.info("Processing %s records", len(df))

        for _, row in df.iterrows():
            text = str(row["text"])
            if not text.strip():
                continue

            prediction = predict(text)
            confidence = prediction["confidence"]

            if confidence < settings.confidence_threshold:
                category = "needs_review"
            else:
                category = prediction["category"]

            created_at = pd.to_datetime(row["created_at"], errors="coerce")
            resolved_at = (
                pd.to_datetime(row["resolved_at"], errors="coerce")
                if pd.notna(row["resolved_at"])
                else None
            )

            db.add(
                Complaint(
                    text=text,
                    category=category,
                    confidence=confidence,
                    created_at=created_at,
                    resolved_at=resolved_at,
                )
            )

        db.commit()
        logger.info("CSV processing completed")

    except Exception as exc:
        logger.error("CSV processing failed: %s", exc)
        db.rollback()

    finally:
        db.close()


@router.post("/upload")
def upload_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
):
    destination = _safe_upload_path(file.filename or "upload.csv")
    with destination.open("wb") as handle:
        handle.write(file.file.read())

    if os.getenv("TESTING") == "1":
        process_csv(str(destination))
    else:
        background_tasks.add_task(process_csv, str(destination))

    return {"message": "File received. Processing in background."}


@router.get("/analytics/summary")
def analytics_summary(db: Session = Depends(get_db)):
    return get_summary(db)


@router.get("/complaints")
def get_complaints(db: Session = Depends(get_db)):
    data = db.query(Complaint).order_by(Complaint.id.desc()).limit(100).all()

    return [
        {
            "text": complaint.text,
            "category": complaint.category,
            "confidence": complaint.confidence,
            "created_at": complaint.created_at,
            "resolved_at": complaint.resolved_at,
        }
        for complaint in data
    ]
