from fastapi import FastAPI
from backend.core.database import engine
from backend.models import complaint
from backend.api.routes import router   # ✅ IMPORTANT

# Create tables
complaint.Base.metadata.create_all(bind=engine)

app = FastAPI()

# 🔥 THIS LINE IS THE KEY
app.include_router(router)


@app.get("/health")
def health():
    return {"status": "ok"}