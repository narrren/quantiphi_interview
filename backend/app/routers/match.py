"""Tech Stack Compatibility ("The Vibe Check") endpoint."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.schemas.match import MatchRequest, MatchResponse
from app.services import portfolio_service, settings_service
from app.services.match_service import compute_match

router = APIRouter(tags=["match"])


@router.post("/match", response_model=MatchResponse)
def match_job_description(body: MatchRequest) -> dict[str, Any]:
    """Score the user's repositories against a job description and remember the JD in settings."""
    portfolio = portfolio_service.get_portfolio(body.username)
    result = compute_match(portfolio, body.job_description)
    settings_service.update_settings({"last_job_description": body.job_description})
    return result
