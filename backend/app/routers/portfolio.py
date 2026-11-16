"""Portfolio endpoint."""
from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query

from app.core.config import USERNAME_PATTERN
from app.schemas.portfolio import PortfolioOut
from app.services.portfolio_service import get_portfolio

router = APIRouter(tags=["portfolio"])


@router.get("/portfolio/{username}", response_model=PortfolioOut)
def read_portfolio(
    username: Annotated[str, Path(pattern=USERNAME_PATTERN)],
    refresh: Annotated[bool, Query()] = False,
) -> dict[str, Any]:
    """Return profile, stats, repositories and contributions (cached in SQLite)."""
    return get_portfolio(username, refresh=refresh)
