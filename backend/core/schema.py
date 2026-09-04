import logging

from sqlalchemy import inspect, text

from backend.core.database import engine

logger = logging.getLogger(__name__)

# Only one non-failed job may own a given content hash (SQLite partial unique index).
ACTIVE_HASH_INDEX = "uq_ingestion_jobs_content_hash_active"


def ensure_schema() -> None:
    """Create tables and apply lightweight SQLite column upgrades."""
    from backend.models import complaint, job  # noqa: F401

    complaint.Base.metadata.create_all(bind=engine)

    if not engine.url.drivername.startswith("sqlite"):
        return

    inspector = inspect(engine)
    tables = set(inspector.get_table_names())

    with engine.begin() as conn:
        if "complaints" in tables:
            columns = {col["name"] for col in inspector.get_columns("complaints")}
            if "job_id" not in columns:
                logger.info("Adding complaints.job_id column")
                conn.execute(text("ALTER TABLE complaints ADD COLUMN job_id VARCHAR(36)"))
            if "needs_review" not in columns:
                logger.info("Adding complaints.needs_review column")
                conn.execute(
                    text(
                        "ALTER TABLE complaints ADD COLUMN needs_review BOOLEAN "
                        "NOT NULL DEFAULT 0"
                    )
                )
                # Legacy rows stored "needs_review" as category — migrate flag, keep label.
                conn.execute(
                    text(
                        "UPDATE complaints SET needs_review = 1 "
                        "WHERE lower(coalesce(category, '')) = 'needs_review'"
                    )
                )
            if "human_reviewed" not in columns:
                logger.info("Adding complaints.human_reviewed column")
                conn.execute(
                    text(
                        "ALTER TABLE complaints ADD COLUMN human_reviewed BOOLEAN "
                        "NOT NULL DEFAULT 0"
                    )
                )

        if "ingestion_jobs" in tables:
            job_cols = {
                col["name"] for col in inspect(engine).get_columns("ingestion_jobs")
            }
            alterations = {
                "error_rows": "ALTER TABLE ingestion_jobs ADD COLUMN error_rows INTEGER DEFAULT 0",
                "quality_summary": "ALTER TABLE ingestion_jobs ADD COLUMN quality_summary TEXT",
                "content_hash": "ALTER TABLE ingestion_jobs ADD COLUMN content_hash VARCHAR(64)",
                "source_path": "ALTER TABLE ingestion_jobs ADD COLUMN source_path VARCHAR(512)",
            }
            for column, ddl in alterations.items():
                if column not in job_cols:
                    logger.info("Adding ingestion_jobs.%s column", column)
                    conn.execute(text(ddl))

            indexes = {idx["name"] for idx in inspect(engine).get_indexes("ingestion_jobs")}
            if ACTIVE_HASH_INDEX not in indexes:
                logger.info("Creating partial unique index %s", ACTIVE_HASH_INDEX)
                conn.execute(
                    text(
                        f"CREATE UNIQUE INDEX IF NOT EXISTS {ACTIVE_HASH_INDEX} "
                        "ON ingestion_jobs(content_hash) "
                        "WHERE content_hash IS NOT NULL "
                        "AND status IN ('pending', 'processing', 'completed')"
                    )
                )
