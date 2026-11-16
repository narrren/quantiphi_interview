"""Embeddable SVG badge endpoint."""
from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Path, Query, Response

from app.core.config import USERNAME_PATTERN
from app.services import badge_service, portfolio_service

router = APIRouter(tags=["badge"])

BadgeMetric = Literal["stars", "followers", "contributions", "streak", "top_language"]


@router.get(
    "/badge/{username}",
    response_class=Response,
    responses={200: {"content": {"image/svg+xml": {}}, "description": "SVG badge"}},
)
def read_badge(
    username: Annotated[str, Path(pattern=USERNAME_PATTERN)],
    metric: Annotated[BadgeMetric, Query()] = "stars",
    style: Annotated[Literal["flat"], Query()] = "flat",
) -> Response:
    """Return a shields.io-style flat SVG badge for one portfolio metric."""
    portfolio = portfolio_service.get_portfolio(username)
    label, value, color = badge_service.badge_for(portfolio, metric)
    return Response(
        content=badge_service.render_badge(label, value, color),
        media_type="image/svg+xml",
        headers={"Cache-Control": "public, max-age=3600"},
    )
