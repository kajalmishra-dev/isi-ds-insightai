"""CSV export helpers for complaints and jobs."""

from __future__ import annotations

import csv
import io
from datetime import datetime

from sqlalchemy.orm import Session

from backend.models.complaint import Complaint
from backend.services.analytics import build_complaint_query


EXPORT_COLUMNS = [
    "id",
    "text",
    "category",
    "confidence",
    "needs_review",
    "job_id",
    "created_at",
    "resolved_at",
]


def _fmt(value) -> str:
    if value is None:
        return ""
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    return str(value)


def complaints_to_csv(rows: list[Complaint]) -> str:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=EXPORT_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow(
            {
                "id": row.id,
                "text": row.text,
                "category": row.category,
                "confidence": "" if row.confidence is None else f"{row.confidence:.6f}",
                "needs_review": "true" if row.needs_review else "false",
                "job_id": row.job_id or "",
                "created_at": _fmt(row.created_at),
                "resolved_at": _fmt(row.resolved_at),
            }
        )
    return buffer.getvalue()


def export_job_complaints(db: Session, job_id: str) -> str:
    rows = (
        db.query(Complaint)
        .filter(Complaint.job_id == job_id)
        .order_by(Complaint.id.asc())
        .all()
    )
    return complaints_to_csv(rows)


def export_filtered_complaints(
    db: Session,
    *,
    category: str | None = None,
    search: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    needs_review: bool | None = None,
    min_confidence: float | None = None,
    max_confidence: float | None = None,
    limit: int = 5000,
) -> str:
    query = build_complaint_query(
        db,
        category=category,
        search=search,
        date_from=date_from,
        date_to=date_to,
        needs_review=needs_review,
        min_confidence=min_confidence,
        max_confidence=max_confidence,
    )
    rows = query.order_by(Complaint.id.desc()).limit(limit).all()
    return complaints_to_csv(rows)
