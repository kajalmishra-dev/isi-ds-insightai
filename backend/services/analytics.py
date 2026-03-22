from sqlalchemy.orm import Session
from backend.models.complaint import Complaint
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)

def get_summary(db: Session):
    total = db.query(Complaint).count()

    categories = (
        db.query(Complaint.category, func.count(Complaint.id))
        .group_by(Complaint.category)
        .all()
    )

    category_distribution = {
        cat: count / total * 100 if total else 0
        for cat, count in categories
    }

    resolved = db.query(Complaint).filter(
        Complaint.resolved_at.isnot(None)
    ).all()

    within_24h = 0

    for c in resolved:
        if (c.resolved_at - c.created_at).total_seconds() <= 86400:
            within_24h += 1

    north_star = (
        within_24h / len(resolved) * 100 if resolved else 0
    )

    top_issues = sorted(
        category_distribution.items(),
        key=lambda x: x[1],
        reverse=True
    )[:3]

    return {
        "total_complaints": total,
        "category_distribution": category_distribution,
        "north_star_metric": north_star,
        "top_issues": top_issues
    }