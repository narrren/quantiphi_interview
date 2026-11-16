"""User settings with defaults; validation is shared with the API schema."""
from __future__ import annotations

from typing import Any

from app.core.config import settings as app_config
from app.repositories import settings_repository
from app.schemas.portfolio import SettingsUpdate


def _defaults() -> dict[str, Any]:
    return {
        "default_username": "",
        "theme": "dark",
        "cache_ttl_seconds": app_config.default_cache_ttl,
        "last_job_description": "",
    }


def get_settings() -> dict[str, Any]:
    """Return the full settings object (stored values layered over defaults)."""
    merged = _defaults()
    stored = settings_repository.get_all()
    merged.update({key: stored[key] for key in merged if key in stored})
    return merged


def update_settings(partial: dict[str, Any]) -> dict[str, Any]:
    """Validate and persist a partial update (unknown/null keys ignored); return full settings."""
    changes = SettingsUpdate.model_validate(partial).model_dump(exclude_none=True)
    if changes:
        settings_repository.set_many(changes)
    return get_settings()
