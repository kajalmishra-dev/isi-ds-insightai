from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Complaint(Base):
    __tablename__ = "complaints"

    id = Column(Integer, primary_key=True, index=True)
    text = Column(Text, nullable=False)
    # Always the model (or human-corrected) category — never overwrite with "needs_review".
    category = Column(String(64), nullable=True, index=True)
    confidence = Column(Float, nullable=True)
    needs_review = Column(Boolean, nullable=False, default=False, index=True)
    # Set when a human clears the review queue (approve or reclassify).
    human_reviewed = Column(Boolean, nullable=False, default=False, index=True)
    job_id = Column(String(36), ForeignKey("ingestion_jobs.id"), nullable=True, index=True)

    created_at = Column(DateTime, default=utcnow, index=True)
    resolved_at = Column(DateTime, nullable=True)

    job = relationship("IngestionJob", back_populates="complaints")
