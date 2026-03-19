from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
import pandas as pd

from backend.schemas.complaint import ComplaintRequest, ComplaintResponse
from backend.core.deps import get_db
from backend.models.complaint import Complaint
from ml.engine import predict

# 🔥 THIS MUST COME BEFORE ANY @router
router = APIRouter()
@router.post("/upload")
def upload_csv(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    try:
        df = pd.read_csv(file.file)

        if "text" not in df.columns:
            return {"error": "CSV must contain 'text' column"}

        logger.info(f"Processing {len(df)} records")

        count = 0

        for _, row in df.iterrows():
            text = row["text"]

            if pd.isna(text) or not str(text).strip():
                continue

            text = str(text)

            prediction = predict(text)

            complaint = Complaint(
                text=text,
                category=prediction["category"],
                confidence=prediction["confidence"]
            )

            db.add(complaint)
            count += 1

        db.commit()

        return {
            "message": "File processed successfully",
            "processed_records": count
        }

    except Exception as e:
        logger.error(str(e))
        return {"error": "File processing failed"}