import os
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

# Load project-root .env if present. Existing process env wins (override=False).
_ENV_FILE = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(dotenv_path=_ENV_FILE, override=False)


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() in {"1", "true", "yes"}


def _env_float(name: str, default: str) -> float:
    raw = os.getenv(name, default)
    try:
        return float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a float, got {raw!r}") from exc


def _env_int(name: str, default: str) -> int:
    raw = os.getenv(name, default)
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from exc


class Settings:
    app_name: str
    app_version: str
    environment: str
    database_url: str
    confidence_threshold: float
    upload_dir: str
    max_upload_bytes: int
    api_key: str
    auth_enabled: bool
    cors_origins: list[str]
    default_page_size: int
    max_page_size: int

    def __init__(self) -> None:
        self.app_name = os.getenv("APP_NAME", "InsightAI")
        self.app_version = os.getenv("APP_VERSION", "2.1.0")
        self.environment = os.getenv("ENVIRONMENT", "development")

        self.database_url = os.getenv("DATABASE_URL", "sqlite:///./insight.db")
        self.confidence_threshold = _env_float("CONFIDENCE_THRESHOLD", "0.32")
        if not 0.0 <= self.confidence_threshold <= 1.0:
            raise ValueError("CONFIDENCE_THRESHOLD must be between 0 and 1")
        # Clear top-1 vs top-2 winners skip review even when max-prob is soft.
        self.confidence_margin = _env_float("CONFIDENCE_MARGIN", "0.10")
        if not 0.0 <= self.confidence_margin <= 1.0:
            raise ValueError("CONFIDENCE_MARGIN must be between 0 and 1")

        self.upload_dir = os.getenv("UPLOAD_DIR", "data/uploads")
        self.max_upload_bytes = _env_int("MAX_UPLOAD_BYTES", str(10 * 1024 * 1024))
        if self.max_upload_bytes <= 0:
            raise ValueError("MAX_UPLOAD_BYTES must be positive")

        self.api_key = os.getenv("API_KEY", "").strip()
        self.auth_enabled = _env_bool("AUTH_ENABLED", "false")

        if self.auth_enabled and not self.api_key:
            raise ValueError(
                "AUTH_ENABLED is true but API_KEY is empty. "
                "Set a strong API_KEY or disable AUTH_ENABLED."
            )

        # Shared / staging must not silently run open (opt out only for demos).
        if self.environment.lower() in {"production", "staging"} and not self.auth_enabled:
            if _env_bool("REQUIRE_AUTH_IN_PRODUCTION", "true"):
                raise ValueError(
                    f"ENVIRONMENT={self.environment} requires AUTH_ENABLED=true "
                    "(or set REQUIRE_AUTH_IN_PRODUCTION=false for local demos)."
                )
            import logging

            logging.getLogger(__name__).warning(
                "ENVIRONMENT=%s with AUTH_ENABLED=false - API is open. "
                "Enable auth for any shared deploy.",
                self.environment,
            )

        raw_cors = os.getenv(
            "CORS_ORIGINS",
            "http://127.0.0.1:8501,http://localhost:8501,http://127.0.0.1:8502,http://localhost:8502",
        ).strip()
        # "*" allows any browser origin (public demos / Render UI hostname).
        if raw_cors == "*":
            self.cors_origins = ["*"]
        else:
            self.cors_origins = [
                origin.strip() for origin in raw_cors.split(",") if origin.strip()
            ]

        self.default_page_size = _env_int("DEFAULT_PAGE_SIZE", "50")
        self.max_page_size = _env_int("MAX_PAGE_SIZE", "200")
        if self.default_page_size < 1 or self.max_page_size < 1:
            raise ValueError("DEFAULT_PAGE_SIZE and MAX_PAGE_SIZE must be >= 1")
        if self.default_page_size > self.max_page_size:
            raise ValueError("DEFAULT_PAGE_SIZE cannot exceed MAX_PAGE_SIZE")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
