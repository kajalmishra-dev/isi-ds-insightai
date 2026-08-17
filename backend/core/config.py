import os
from functools import lru_cache


@lru_cache
def get_settings():
    return Settings()


class Settings:
    database_url: str = os.getenv("DATABASE_URL", "sqlite:///./insight.db")
    confidence_threshold: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.6"))
    upload_dir: str = os.getenv("UPLOAD_DIR", "data/uploads")


settings = get_settings()
