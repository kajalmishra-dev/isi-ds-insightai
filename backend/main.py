import logging
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.api.routes import router
from backend.core.config import settings
from backend.core.database import SessionLocal
from backend.core.logging_config import configure_logging
from backend.core.schema import ensure_schema
from backend.schemas.complaint import HealthResponse, ReadyResponse
from backend.services.jobs import reclaim_stuck_jobs

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_schema()
    with SessionLocal() as session:
        reclaimed = reclaim_stuck_jobs(session)
        if reclaimed:
            logger.warning("Startup reclaim: marked %s stuck job(s) as failed", reclaimed)
    logger.info(
        "InsightAI %s starting (env=%s, auth_enabled=%s)",
        settings.app_version,
        settings.environment,
        settings.auth_enabled,
    )
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Production-style complaint intelligence API: CSV ingestion, "
        "ML classification, analytics, job tracking, export, and retry."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid4()))
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - started) * 1000.0
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Response-Time-Ms"] = f"{duration_ms:.1f}"
    # Avoid logging complaint bodies / upload payloads — path + status only.
    logger.info(
        "request_id=%s method=%s path=%s status=%s duration_ms=%.1f",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, (HTTPException, StarletteHTTPException)):
        return await http_exception_handler(request, exc)
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )


app.include_router(router, prefix="/api/v1", tags=["v1"])
app.include_router(router, prefix="", include_in_schema=False)


@app.get("/health", response_model=HealthResponse, tags=["ops"])
def health():
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        environment=settings.environment,
    )


@app.get("/ready", response_model=ReadyResponse, tags=["ops"])
def ready():
    db_ok = False
    model_ok = False
    model_version = None
    detail = None

    try:
        with SessionLocal() as session:
            session.execute(text("SELECT 1"))
        db_ok = True
    except Exception as exc:
        detail = f"database: {exc}"

    try:
        from ml.engine import get_engine, get_model_version

        engine = get_engine()
        model_ok = True
        model_version = getattr(engine, "model_version", None) or get_model_version()
    except Exception as exc:
        detail = (detail + "; " if detail else "") + f"model: {exc}"

    status = "ready" if db_ok and model_ok else "not_ready"
    return ReadyResponse(
        status=status,
        database=db_ok,
        model=model_ok,
        model_version=model_version,
        detail=detail,
    )
