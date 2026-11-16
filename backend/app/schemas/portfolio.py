"""Pydantic models for the portfolio and settings endpoints (see docs/API_CONTRACT.md)."""
from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from app.core.config import USERNAME_PATTERN

_USERNAME_RE = re.compile(USERNAME_PATTERN)


class Profile(BaseModel):
    login: str
    name: str | None = None
    avatar_url: str | None = None
    bio: str | None = None
    company: str | None = None
    location: str | None = None
    blog: str | None = None
    html_url: str
    followers: int = 0
    following: int = 0
    public_repos: int = 0
    created_at: str | None = None


class LanguageStat(BaseModel):
    name: str
    count: int
    percentage: float
    color: str


class Stats(BaseModel):
    total_stars: int
    total_forks: int
    total_repos: int
    top_languages: list[LanguageStat]


class Repository(BaseModel):
    id: int
    name: str
    full_name: str
    description: str | None = None
    html_url: str
    stars: int
    forks: int
    language: str | None = None
    language_color: str | None = None
    topics: list[str]
    updated_at: str | None = None
    is_fork: bool
    license: str | None = None
    homepage: str | None = None
    archived: bool = False
    open_issues: int = 0


class ContributionDay(BaseModel):
    date: str
    count: int
    level: int = Field(ge=0, le=4)


class BestDay(BaseModel):
    date: str
    count: int


class Contributions(BaseModel):
    total: int
    weeks: list[list[ContributionDay]]
    current_streak: int
    longest_streak: int
    best_day: BestDay | None = None
    source: Literal["graphql", "scrape", "unavailable"]


class CacheInfo(BaseModel):
    cached: bool
    fetched_at: str
    ttl_seconds: int
    stale: bool


class PortfolioOut(BaseModel):
    profile: Profile
    stats: Stats
    repositories: list[Repository]
    contributions: Contributions
    cache: CacheInfo


class SettingsOut(BaseModel):
    default_username: str
    theme: Literal["light", "dark"]
    cache_ttl_seconds: int
    last_job_description: str


class SettingsUpdate(BaseModel):
    """Partial settings update; omitted (or null) fields are left unchanged."""

    default_username: str | None = None
    theme: Literal["light", "dark"] | None = None
    cache_ttl_seconds: int | None = Field(default=None, ge=60, le=86400)
    last_job_description: str | None = Field(default=None, max_length=20000)

    @field_validator("default_username")
    @classmethod
    def _validate_username(cls, value: str | None) -> str | None:
        if value is None:
            return None
        value = value.strip()
        if value and not _USERNAME_RE.fullmatch(value):
            raise ValueError("Invalid GitHub username")
        return value
