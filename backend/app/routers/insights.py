"""Developer insights and portfolio readiness endpoint."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query

from app.core.config import USERNAME_PATTERN
from app.schemas.insights import InsightsOut
from app.services import insights_service

router = APIRouter(tags=["insights"])


@router.get("/insights/{username}", response_model=InsightsOut)
def read_insights(
    username: Annotated[str, Path(pattern=USERNAME_PATTERN)],
    refresh: Annotated[bool, Query()] = False,
) -> dict[str, Any]:
    """Return activity patterns and a portfolio readiness score for `username`."""
    return insights_service.get_insights(username, refresh=refresh)
