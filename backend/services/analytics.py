from sqlalchemy.orm import Session
from sqlalchemy import func
from backend.models.complaint import Complaint
import logging

logger = logging.getLogger(__name__)


def get_summary(db: Session):
    try:
        total = db.query(func.count(Complaint.id)).scalar() or 0

        categories = (
            db.query(Complaint.category, func.count(Complaint.id))
            .group_by(Complaint.category)
            .all()
        )

        category_distribution = {
            cat: round((count / total) * 100, 2) if total else 0
            for cat, count in categories
        }

        resolved = db.query(Complaint).filter(
            Complaint.resolved_at.isnot(None)
        ).all()

        within_24h = sum(
            1 for c in resolved
            if c.created_at and c.resolved_at and
            (c.resolved_at - c.created_at).total_seconds() <= 86400
        )

        north_star = round(
            (within_24h / total) * 100, 2
        ) if total else 0

        top_issues = [
            {"category": cat, "count": count}
            for cat, count in sorted(categories, key=lambda x: x[1], reverse=True)[:3]
        ]

        return {
            "total_complaints": total,
            "category_distribution": category_distribution,
            "north_star_metric": north_star,
            "top_issues": top_issues
        }

    except Exception as e:
        logger.error(f"Analytics failed: {str(e)}")
        return {
            "total_complaints": 0,
            "category_distribution": {},
            "north_star_metric": 0,
            "top_issues": []
        }