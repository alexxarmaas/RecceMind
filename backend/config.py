from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _as_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _as_int(value: str | None, default: int) -> int:
    try:
        return int(value) if value is not None else default
    except ValueError:
        return default


def _as_float(value: str | None, default: float) -> float:
    try:
        return float(value) if value is not None else default
    except ValueError:
        return default


def _origins(value: str | None) -> tuple[str, ...]:
    if not value:
        return ("http://localhost:8081", "http://127.0.0.1:8081")
    return tuple(item.strip() for item in value.split(",") if item.strip())


@dataclass(frozen=True)
class Settings:
    google_maps_api_key: str = os.getenv("GOOGLE_MAPS_API_KEY", "")
    database_url: str = os.getenv(
        "DATABASE_URL",
        f"sqlite:///{(BASE_DIR / 'recce_mind.db').as_posix()}",
    )
    allowed_origins: tuple[str, ...] = _origins(os.getenv("ALLOWED_ORIGINS"))
    max_upload_bytes: int = _as_int(os.getenv("MAX_UPLOAD_BYTES"), 10 * 1024 * 1024)
    external_request_timeout_seconds: float = _as_float(
        os.getenv("EXTERNAL_REQUEST_TIMEOUT_SECONDS"), 15.0
    )
    auto_create_db: bool = _as_bool(os.getenv("AUTO_CREATE_DB"), True)
    service_token: str = os.getenv("RECCEMIND_SERVICE_TOKEN", "").strip()


settings = Settings()
