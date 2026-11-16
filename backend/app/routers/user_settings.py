"""Settings endpoints."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.schemas.portfolio import SettingsOut, SettingsUpdate
from app.services.settings_service import get_settings, update_settings

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=SettingsOut)
def read_settings() -> dict[str, Any]:
    """Return the current settings."""
    return get_settings()


@router.put("/settings", response_model=SettingsOut)
def write_settings(body: SettingsUpdate) -> dict[str, Any]:
    """Apply a partial settings update and return the full settings object."""
    return update_settings(body.model_dump(exclude_none=True))
