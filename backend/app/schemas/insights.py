"""Pydantic models for the insights endpoint (see docs/API_CONTRACT.md, v2 additions)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class WeekdayTotal(BaseModel):
    day: Literal["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    total: int
    average: float


class MonthlyTotal(BaseModel):
    month: str
    label: str
    total: int


class Trend(BaseModel):
    last_30_days: int
    previous_30_days: int
    change_percentage: float | None = None
    direction: Literal["up", "down", "flat"]


class Activity(BaseModel):
    weekday_totals: list[WeekdayTotal]
    monthly: list[MonthlyTotal]
    active_days: int
    total_days: int
    consistency_percentage: float
    average_per_active_day: float
    most_active_weekday: str | None = None
    trend: Trend


class ReadinessCheck(BaseModel):
    id: str
    label: str
    passed: bool
    detail: str


class RepositoryReadiness(BaseModel):
    name: str
    score: int
    issues: list[str]


class Readiness(BaseModel):
    score: int
    grade: Literal["Excellent", "Strong", "Moderate", "Low"]
    checks: list[ReadinessCheck]
    recommendations: list[str]
    repositories: list[RepositoryReadiness]


class InsightsOut(BaseModel):
    activity: Activity
    readiness: Readiness
