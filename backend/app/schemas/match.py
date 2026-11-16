"""Request/response models for POST /api/match (Tech Stack Compatibility)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.core.config import USERNAME_PATTERN
from app.services.tech_keywords import Category


class MatchRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    username: str = Field(pattern=USERNAME_PATTERN)
    job_description: str = Field(min_length=20, max_length=20000)


class MatchedKeyword(BaseModel):
    keyword: str
    category: Category
    evidence: list[str]


class MissingKeyword(BaseModel):
    keyword: str
    category: Category


class MatchResponse(BaseModel):
    match_percentage: int = Field(ge=0, le=100)
    grade: Literal["Excellent", "Strong", "Moderate", "Low"]
    matched: list[MatchedKeyword]
    missing: list[MissingKeyword]
    jd_keywords_count: int
    summary: str
