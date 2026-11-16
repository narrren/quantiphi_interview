"""Unit tests for contribution parsing, weekly grouping and streak computation."""
from __future__ import annotations

from datetime import date

from app.services import contributions
from app.services.contributions import (
    build_weeks,
    compute_streaks,
    parse_contributions_html,
    parse_graphql_calendar,
)

HTML_FIXTURE = """
<table><tbody><tr>
  <td tabindex="0" data-ix="0" data-date="2025-11-16" id="contribution-day-component-0-0"
      data-level="1" class="ContributionCalendar-day"></td>
  <td id="contribution-day-component-1-0" data-level="0" data-date="2025-11-17"
      class="ContributionCalendar-day"></td>
  <td class="ContributionCalendar-day" data-level="4" data-date="2025-11-18"
      id="contribution-day-component-2-0"></td>
  <td class="ContributionCalendar-label">Mon</td>
</tr></tbody></table>
<tool-tip id="tooltip-1" for="contribution-day-component-0-0" popover="manual">5 contributions on November 16th.</tool-tip>
<tool-tip for="contribution-day-component-1-0" id="tooltip-2">No contributions on November 17th.</tool-tip>
<tool-tip for="contribution-day-component-2-0" id="tooltip-3">1,204 contributions on November 18th.</tool-tip>
"""


def _day(iso: str, count: int, level: int = 1) -> dict:
    return {"date": iso, "count": count, "level": level}


def test_parse_html_matches_tooltips_regardless_of_attribute_order() -> None:
    assert parse_contributions_html(HTML_FIXTURE) == [
        _day("2025-11-16", 5, 1),
        _day("2025-11-17", 0, 0),
        _day("2025-11-18", 1204, 4),
    ]


def test_parse_html_without_calendar_returns_empty() -> None:
    assert parse_contributions_html("<html><body>nothing</body></html>") == []


def test_parse_graphql_calendar_maps_levels() -> None:
    calendar = {
        "totalContributions": 3,
        "weeks": [
            {"contributionDays": [
                {"date": "2025-11-17", "contributionCount": 0, "contributionLevel": "NONE"},
                {"date": "2025-11-16", "contributionCount": 3, "contributionLevel": "FOURTH_QUARTILE"},
            ]}
        ],
    }
    assert parse_graphql_calendar(calendar) == [_day("2025-11-16", 3, 4), _day("2025-11-17", 0, 0)]


def test_fetch_falls_back_to_unavailable_without_raising(monkeypatch) -> None:
    from app.core.errors import UpstreamError

    def boom(_: str) -> str:
        raise UpstreamError("offline")

    monkeypatch.setattr(contributions.github_client, "fetch_contribution_calendar", boom)
    monkeypatch.setattr(contributions.github_client, "fetch_contributions_html", boom)
    assert contributions.fetch_contribution_days("octocat", use_graphql=True) == ([], "unavailable")


def test_fetch_uses_scrape_when_no_token(monkeypatch) -> None:
    monkeypatch.setattr(contributions.github_client, "fetch_contributions_html", lambda _: HTML_FIXTURE)
    days, source = contributions.fetch_contribution_days("octocat", use_graphql=False)
    assert source == "scrape" and len(days) == 3


def test_build_weeks_groups_sunday_to_saturday() -> None:
    # 2025-11-15 is a Saturday, 2025-11-16 a Sunday, 2025-11-22 a Saturday.
    days = [_day("2025-11-22", 1), _day("2025-11-16", 1), _day("2025-11-15", 1), _day("2025-11-23", 1)]
    weeks = build_weeks(days)
    assert [[d["date"] for d in week] for week in weeks] == [
        ["2025-11-15"],
        ["2025-11-16", "2025-11-22"],
        ["2025-11-23"],
    ]
    assert build_weeks([]) == []


def test_streaks_ending_today() -> None:
    days = [_day("2026-11-13", 2), _day("2026-11-14", 0), _day("2026-11-15", 1), _day("2026-11-16", 7)]
    result = compute_streaks(days, date(2026, 11, 16))
    assert result == {
        "total": 10,
        "current_streak": 2,
        "longest_streak": 2,
        "best_day": {"date": "2026-11-16", "count": 7},
    }


def test_current_streak_ends_yesterday_when_today_is_zero() -> None:
    days = [_day("2026-11-14", 1), _day("2026-11-15", 1), _day("2026-11-16", 0)]
    assert compute_streaks(days, date(2026, 11, 16))["current_streak"] == 2


def test_current_streak_broken_before_yesterday() -> None:
    days = [_day("2026-11-10", 1), _day("2026-11-11", 1), _day("2026-11-12", 1), _day("2026-11-15", 0)]
    result = compute_streaks(days, date(2026, 11, 16))
    assert result["current_streak"] == 0
    assert result["longest_streak"] == 3


def test_longest_streak_requires_consecutive_dates() -> None:
    days = [_day("2026-01-01", 1), _day("2026-01-03", 1), _day("2026-01-04", 1)]
    assert compute_streaks(days, date(2026, 11, 16))["longest_streak"] == 2


def test_streaks_empty_and_all_zero() -> None:
    empty = {"total": 0, "current_streak": 0, "longest_streak": 0, "best_day": None}
    assert compute_streaks([], date(2026, 11, 16)) == empty
    assert compute_streaks([_day("2026-11-16", 0, 0)], date(2026, 11, 16)) == empty
