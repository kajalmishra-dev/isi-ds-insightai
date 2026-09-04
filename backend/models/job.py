from datetime import datetime, timezone

from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.orm import relationship

from backend.core.database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id = Column(String(36), primary_key=True)
    filename = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="pending", index=True)
    total_rows = Column(Integer, default=0)
    processed_rows = Column(Integer, default=0)
    skipped_rows = Column(Integer, default=0)
    error_rows = Column(Integer, default=0)
    error_message = Column(Text, nullable=True)
    quality_summary = Column(Text, nullable=True)
    content_hash = Column(String(64), nullable=True, index=True)
    source_path = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    complaints = relationship("Complaint", back_populates="job")
