"""Contribution calendar: fetching (GraphQL or HTML scrape), parsing, weekly grouping and streaks."""
from __future__ import annotations

import logging
import re
from datetime import date, timedelta
from typing import Any

from app.core.errors import AppError
from app.services import github_client

logger = logging.getLogger(__name__)

Day = dict[str, Any]  # {"date": "YYYY-MM-DD", "count": int, "level": 0..4}

GRAPHQL_LEVELS = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

_TD_RE = re.compile(r"<td\b[^>]*>", re.IGNORECASE)
_TOOLTIP_RE = re.compile(r"<tool-tip\b([^>]*)>(.*?)</tool-tip>", re.IGNORECASE | re.DOTALL)
_COUNT_RE = re.compile(r"([\d,]+)\s+contributions?", re.IGNORECASE)


def _attr(tag: str, name: str) -> str | None:
    """Extract an attribute value from a single HTML start tag, regardless of attribute order."""
    match = re.search(rf'\s{re.escape(name)}\s*=\s*"([^"]*)"', tag)
    return match.group(1) if match else None


def parse_contributions_html(html: str) -> list[Day]:
    """Parse GitHub's public contribution calendar markup into a date-sorted list of days."""
    counts: dict[str, int] = {}
    for attrs, text in _TOOLTIP_RE.findall(html):
        target = _attr(attrs, "for")
        if target is None:
            continue
        match = _COUNT_RE.search(text)
        counts[target] = int(match.group(1).replace(",", "")) if match else 0

    days: list[Day] = []
    for tag in _TD_RE.findall(html):
        day = _attr(tag, "data-date")
        if day is None:
            continue
        level = int(_attr(tag, "data-level") or 0)
        cell_id = _attr(tag, "id")
        days.append(
            {
                "date": day,
                "count": counts.get(cell_id, 0) if cell_id else 0,
                "level": max(0, min(level, 4)),
            }
        )
    return sorted(days, key=lambda d: d["date"])


def parse_graphql_calendar(calendar: dict[str, Any]) -> list[Day]:
    """Flatten a GraphQL contributionCalendar into a date-sorted list of days."""
    days = [
        {
            "date": d["date"],
            "count": int(d["contributionCount"]),
            "level": GRAPHQL_LEVELS.get(d.get("contributionLevel", "NONE"), 0),
        }
        for week in calendar.get("weeks", [])
        for d in week.get("contributionDays", [])
    ]
    return sorted(days, key=lambda d: d["date"])


def fetch_contribution_days(username: str, use_graphql: bool) -> tuple[list[Day], str]:
    """Fetch contribution days and their source; never raises (falls back to 'unavailable')."""
    if use_graphql:
        try:
            return parse_graphql_calendar(github_client.fetch_contribution_calendar(username)), "graphql"
        except (AppError, KeyError, TypeError, ValueError) as exc:
            logger.warning("GraphQL contributions failed for %s: %s", username, exc)
    try:
        days = parse_contributions_html(github_client.fetch_contributions_html(username))
        if days:
            return days, "scrape"
        logger.warning("Contribution page for %s contained no calendar cells", username)
    except (AppError, ValueError) as exc:
        logger.warning("Scraping contributions failed for %s: %s", username, exc)
    return [], "unavailable"


def build_weeks(days: list[Day]) -> list[list[Day]]:
    """Group days into weeks (oldest first), each ordered Sunday -> Saturday."""
    weeks: dict[date, list[Day]] = {}
    for day in sorted(days, key=lambda d: d["date"]):
        current = date.fromisoformat(day["date"])
        sunday = current - timedelta(days=(current.weekday() + 1) % 7)
        weeks.setdefault(sunday, []).append(day)
    return [weeks[key] for key in sorted(weeks)]


def compute_streaks(days: list[Day], today: date) -> dict[str, Any]:
    """Compute total, current streak, longest streak and best day.

    The current streak counts consecutive active days ending today, or ending yesterday
    when today has no contributions yet.
    """
    counts = {date.fromisoformat(d["date"]): int(d["count"]) for d in days}

    cursor = today if counts.get(today, 0) > 0 else today - timedelta(days=1)
    current = 0
    while counts.get(cursor, 0) > 0:
        current += 1
        cursor -= timedelta(days=1)

    longest = run = 0
    previous: date | None = None
    for day in sorted(counts):
        if counts[day] > 0:
            run = run + 1 if previous is not None and day - previous == timedelta(days=1) else 1
            previous = day
            longest = max(longest, run)
        else:
            run, previous = 0, None

    best = max(sorted(counts), key=lambda d: counts[d], default=None)
    best_day = (
        {"date": best.isoformat(), "count": counts[best]} if best and counts[best] > 0 else None
    )
    return {
        "total": sum(counts.values()),
        "current_streak": current,
        "longest_streak": longest,
        "best_day": best_day,
    }


def summarize(days: list[Day], source: str, today: date) -> dict[str, Any]:
    """Build the contract's `contributions` object from raw days."""
    stats = compute_streaks(days, today)
    return {
        "total": stats["total"],
        "weeks": build_weeks(days),
        "current_streak": stats["current_streak"],
        "longest_streak": stats["longest_streak"],
        "best_day": stats["best_day"],
        "source": source,
    }
