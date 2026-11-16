"""Application configuration loaded from environment variables."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent


@dataclass(frozen=True)
class Settings:
    github_token: str | None = os.getenv("GITHUB_TOKEN") or None
    github_api_url: str = os.getenv("GITHUB_API_URL", "https://api.github.com")
    db_path: Path = Path(os.getenv("DB_PATH", str(BACKEND_DIR / "data" / "cache.db")))
    default_cache_ttl: int = int(os.getenv("CACHE_TTL_SECONDS", "3600"))
    http_timeout: float = float(os.getenv("HTTP_TIMEOUT", "15"))
    cors_origins: tuple[str, ...] = tuple(
        o.strip()
        for o in os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
        if o.strip()
    )
    frontend_dist: Path = PROJECT_DIR / "frontend" / "dist"


settings = Settings()

USERNAME_PATTERN = r"^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$"
