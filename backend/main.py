from fastapi import FastAPI
from backend.core.database import engine
from backend.models import complaint
from backend.api.routes import router

# Create tables
complaint.Base.metadata.create_all(bind=engine)

app = FastAPI()

# include all routes
app.include_router(router)

@app.get("/health")
def health():
    return {"status": "ok"}