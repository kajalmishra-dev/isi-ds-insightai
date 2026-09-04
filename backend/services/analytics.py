import logging
import math
from datetime import datetime

from sqlalchemy import asc, desc, func
from sqlalchemy.orm import Session

from backend.models.complaint import Complaint
from backend.schemas.complaint import AnalyticsSummary, InsightItem, TopIssue

logger = logging.getLogger(__name__)

SORTABLE_COLUMNS = {
    "id": Complaint.id,
    "created_at": Complaint.created_at,
    "confidence": Complaint.confidence,
    "category": Complaint.category,
}


def _resolution_hours_expr(db: Session):
    """Dialect-aware hours between created_at and resolved_at (SQL-side)."""
    bind = db.get_bind()
    dialect = bind.dialect.name if bind is not None else "sqlite"
    if dialect == "sqlite":
        return (func.julianday(Complaint.resolved_at) - func.julianday(Complaint.created_at)) * 24.0
    return func.extract("epoch", Complaint.resolved_at - Complaint.created_at) / 3600.0


def _median_from_ordered(db: Session, hours_expr, base_query) -> float | None:
    """Median without loading all resolution rows into Python."""
    count = base_query.count()
    if count <= 0:
        return None

    ordered = base_query.order_by(asc(hours_expr))
    if count % 2 == 1:
        value = ordered.offset(count // 2).limit(1).scalar()
        return round(float(value), 2) if value is not None else None

    rows = ordered.offset(count // 2 - 1).limit(2).all()
    if len(rows) < 2:
        return None
    return round((float(rows[0][0]) + float(rows[1][0])) / 2.0, 2)


def build_complaint_query(
    db: Session,
    *,
    category: str | None = None,
    search: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    needs_review: bool | None = None,
    min_confidence: float | None = None,
    max_confidence: float | None = None,
):
    query = db.query(Complaint)

    if category:
        query = query.filter(Complaint.category == category)
    if search:
        query = query.filter(Complaint.text.ilike(f"%{search.strip()}%"))
    if date_from is not None:
        query = query.filter(Complaint.created_at >= date_from)
    if date_to is not None:
        query = query.filter(Complaint.created_at <= date_to)
    if needs_review is True:
        query = query.filter(Complaint.needs_review.is_(True))
    elif needs_review is False:
        query = query.filter(Complaint.needs_review.is_(False))
    if min_confidence is not None:
        query = query.filter(Complaint.confidence >= min_confidence)
    if max_confidence is not None:
        query = query.filter(Complaint.confidence <= max_confidence)

    return query


def list_complaints(
    db: Session,
    *,
    page: int,
    page_size: int,
    category: str | None = None,
    search: str | None = None,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    needs_review: bool | None = None,
    min_confidence: float | None = None,
    max_confidence: float | None = None,
    sort_by: str = "id",
    sort_order: str = "desc",
) -> tuple[list[Complaint], int, int]:
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

    total = query.count()
    total_pages = math.ceil(total / page_size) if page_size and total else (1 if total == 0 else 0)

    column = SORTABLE_COLUMNS.get(sort_by, Complaint.id)
    order_fn = desc if sort_order.lower() == "desc" else asc
    items = (
        query.order_by(order_fn(column))
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return items, total, total_pages


def _build_insights(summary: AnalyticsSummary) -> list[InsightItem]:
    """Actionable anomalies only - do not restate KPI cards."""
    insights: list[InsightItem] = []
    total = summary.total_complaints

    if total == 0:
        return [
            InsightItem(
                code="insufficient_data",
                text="Upload a complaint CSV to begin.",
            )
        ]

    review_rate = summary.low_confidence_rate
    if review_rate >= 80:
        insights.append(
            InsightItem(
                code="review_overload",
                text=(
                    f"Action required: {summary.needs_review_count} of {total} complaints "
                    f"({review_rate:.0f}%) need human review - model confidence is too low "
                    "for automatic triage. Retrain, recalibrate, or lower CONFIDENCE_THRESHOLD."
                ),
            )
        )
    elif review_rate >= 40:
        insights.append(
            InsightItem(
                code="elevated_review",
                text=(
                    f"Elevated review load: {summary.needs_review_count} items "
                    f"({review_rate:.0f}%) are below the confidence threshold."
                ),
            )
        )

    if summary.category_avg_confidence:
        ranked = sorted(
            (
                (cat, conf)
                for cat, conf in summary.category_avg_confidence.items()
                if cat and cat != "needs_review"
            ),
            key=lambda item: item[1],
        )
        if ranked and ranked[0][1] < 0.5:
            weakest, conf = ranked[0]
            weakest_label = str(weakest).replace("_", " ").title()
            insights.append(
                InsightItem(
                    code="weakest_confidence",
                    text=(
                        f"{weakest_label} has very low average model confidence "
                        f"({conf * 100:.1f}%) - check training coverage for this class."
                    ),
                )
            )

    if (
        summary.resolved_count > 0
        and summary.north_star_metric is not None
        and summary.north_star_metric < 50
        and total >= 5
    ):
        insights.append(
            InsightItem(
                code="sla_risk",
                text=(
                    f"SLA risk: only {summary.north_star_metric:.1f}% of complaints "
                    "resolve within 24h."
                ),
            )
        )

    return insights


def get_summary(db: Session) -> AnalyticsSummary:
    """Compute analytics from live data. Raises on failure - never returns fake zeros."""
    try:
        total = db.query(func.count(Complaint.id)).scalar() or 0

        category_rows = (
            db.query(Complaint.category, func.count(Complaint.id))
            .group_by(Complaint.category)
            .all()
        )

        category_distribution = {
            (cat or "unknown"): round((count / total) * 100, 2) if total else 0.0
            for cat, count in category_rows
        }

        resolved_count = (
            db.query(func.count(Complaint.id))
            .filter(Complaint.resolved_at.isnot(None))
            .scalar()
            or 0
        )
        unresolved_count = total - resolved_count

        needs_review_count = (
            db.query(func.count(Complaint.id))
            .filter(Complaint.needs_review.is_(True))
            .scalar()
            or 0
        )
        human_reviewed_count = (
            db.query(func.count(Complaint.id))
            .filter(Complaint.human_reviewed.is_(True))
            .scalar()
            or 0
        )

        hours_expr = _resolution_hours_expr(db)
        resolved_hours_q = (
            db.query(hours_expr.label("hours"))
            .filter(Complaint.resolved_at.isnot(None))
            .filter(hours_expr >= 0)
        )

        avg_raw = resolved_hours_q.with_entities(func.avg(hours_expr)).scalar()
        avg_resolution_hours = round(float(avg_raw), 2) if avg_raw is not None else None
        median_resolution_hours = _median_from_ordered(db, hours_expr, resolved_hours_q)

        within_24h = (
            resolved_hours_q.filter(hours_expr <= 24.0)
            .with_entities(func.count())
            .scalar()
            or 0
        )

        north_star = round((within_24h / total) * 100, 2) if total else 0.0
        resolution_rate = round((resolved_count / total) * 100, 2) if total else 0.0
        low_confidence_rate = (
            round((needs_review_count / total) * 100, 2) if total else 0.0
        )

        avg_confidence = db.query(func.avg(Complaint.confidence)).scalar()
        avg_confidence = (
            round(float(avg_confidence), 4) if avg_confidence is not None else 0.0
        )

        conf_rows = (
            db.query(Complaint.category, func.avg(Complaint.confidence))
            .group_by(Complaint.category)
            .all()
        )
        category_avg_confidence = {
            (cat or "unknown"): round(float(avg or 0.0), 4) for cat, avg in conf_rows
        }

        top_issues = [
            TopIssue(category=cat or "unknown", count=count)
            for cat, count in sorted(category_rows, key=lambda item: item[1], reverse=True)
        ]

        summary = AnalyticsSummary(
            total_complaints=total,
            resolved_count=resolved_count,
            unresolved_count=unresolved_count,
            needs_review_count=needs_review_count,
            human_reviewed_count=human_reviewed_count,
            category_distribution=category_distribution,
            north_star_metric=north_star,
            avg_confidence=avg_confidence,
            top_issues=top_issues,
            resolution_rate=resolution_rate,
            avg_resolution_hours=avg_resolution_hours,
            median_resolution_hours=median_resolution_hours,
            low_confidence_rate=low_confidence_rate,
            within_24h_count=within_24h,
            category_avg_confidence=category_avg_confidence,
            insights=[],
        )
        summary.insights = _build_insights(summary)
        return summary

    except Exception:
        logger.exception("Analytics computation failed")
        raise
