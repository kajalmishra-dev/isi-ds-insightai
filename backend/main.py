import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.api.routes import router
from backend.core.database import engine
from backend.models import complaint

logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(_: FastAPI):
    complaint.Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="InsightAI", lifespan=lifespan)
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}
