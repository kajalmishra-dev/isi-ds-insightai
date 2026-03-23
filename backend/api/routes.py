from fastapi import APIRouter, Depends, UploadFile, File, BackgroundTasks
from sqlalchemy.orm import Session
import pandas as pd
import logging

from backend.core.deps import get_db
from backend.core.database import SessionLocal
from backend.models.complaint import Complaint
from backend.services.analytics import get_summary
from ml.engine import predict

router = APIRouter()
logger = logging.getLogger(__name__)


# =========================
# 🔥 BACKGROUND TASK
# =========================
def process_csv(file_path: str):
    db = SessionLocal()

    try:
        df = pd.read_csv(file_path)

        # ✅ VALIDATION
        required_cols = {"text", "created_at", "resolved_at"}
        if not required_cols.issubset(df.columns):
            logger.error("CSV missing required columns")
            return

        if df.empty:
            logger.warning("CSV is empty")
            return

        logger.info(f"Processing {len(df)} records")

        for _, row in df.iterrows():
            text = str(row["text"])

            if not text.strip():
                continue

            # 🔥 ML PREDICTION
            prediction = predict(text)
            confidence = prediction["confidence"]

            # 🔥 CONFIDENCE THRESHOLD (IMPORTANT)
            if confidence < 0.6:
                category = "needs_review"
            else:
                category = prediction["category"]

            # 🔥 DATE HANDLING
            created_at = pd.to_datetime(row["created_at"], errors="coerce")
            resolved_at = (
                pd.to_datetime(row["resolved_at"], errors="coerce")
                if pd.notna(row["resolved_at"])
                else None
            )

            complaint = Complaint(
                text=text,
                category=category,
                confidence=confidence,
                created_at=created_at,
                resolved_at=resolved_at
            )

            db.add(complaint)

        db.commit()
        logger.info("CSV processing completed")

    except Exception as e:
        logger.error(f"CSV processing failed: {str(e)}")

    finally:
        db.close()


# =========================
# 🔥 UPLOAD ENDPOINT
# =========================
@router.post("/upload")
def upload_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    file_location = f"data/{file.filename}"

    with open(file_location, "wb") as f:
        f.write(file.file.read())

    background_tasks.add_task(process_csv, file_location)

    return {
        "message": "File received. Processing in background."
    }


# =========================
# 🔥 ANALYTICS
# =========================
@router.get("/analytics/summary")
def analytics_summary(db: Session = Depends(get_db)):
    return get_summary(db)


# =========================
# 🔥 RECENT COMPLAINTS
# =========================
@router.get("/complaints")
def get_complaints(db: Session = Depends(get_db)):
    data = db.query(Complaint).order_by(Complaint.id.desc()).limit(100).all()

    return [
        {
            "text": c.text,
            "category": c.category,
            "confidence": c.confidence,
            "created_at": c.created_at,
            "resolved_at": c.resolved_at
        }
        for c in data
    ]