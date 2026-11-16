"""Pydantic models for GET /api/compare (see docs/API_CONTRACT.md, v2 additions)."""
from __future__ import annotations

from pydantic import BaseModel


class CompareDeveloper(BaseModel):
    login: str
    name: str | None = None
    avatar_url: str | None = None
    html_url: str | None = None
    followers: int
    total_stars: int
    total_forks: int
    total_repos: int
    top_language: str | None = None
    total_contributions: int
    current_streak: int
    longest_streak: int


class CompareMetric(BaseModel):
    key: str
    label: str
    values: list[int]
    leader: str | None = None


class CompareOut(BaseModel):
    developers: list[CompareDeveloper]
    metrics: list[CompareMetric]
    shared_languages: list[str]
    summary: str
