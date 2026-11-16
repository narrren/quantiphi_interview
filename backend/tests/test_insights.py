"""Tests for activity insights, readiness scoring, the repositories migration and the endpoint."""
from __future__ import annotations

import dataclasses
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core import database
from app.core.config import settings
from app.main import app
from app.repositories import cache_repository
from app.services import insights_service, portfolio_service
from app.services.insights_service import compute_activity, compute_readiness

TODAY = date(2026, 11, 16)  # a Monday


def _days(start: date, counts: list[int]) -> list[dict[str, Any]]:
    return [
        {"date": (start + timedelta(days=i)).isoformat(), "count": c, "level": min(c, 4)}
        for i, c in enumerate(counts)
    ]


# ---------- activity ----------

def test_weekday_totals_and_averages() -> None:
    # 2026-11-01 is a Sunday; two full weeks with count = weekday index + 1.
    days = _days(date(2026, 11, 1), [i % 7 + 1 for i in range(14)])
    activity = compute_activity(days, TODAY)
    totals = activity["weekday_totals"]
    assert [t["day"] for t in totals] == ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
    assert [t["total"] for t in totals] == [2, 4, 6, 8, 10, 12, 14]
    assert [t["average"] for t in totals] == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0]
    assert activity["most_active_weekday"] == "Sat"
    assert activity["active_days"] == 14 and activity["total_days"] == 14
    assert activity["consistency_percentage"] == 100.0
    assert activity["average_per_active_day"] == 4.0


def test_monthly_buckets_last_12_months_oldest_first() -> None:
    days = [
        {"date": "2025-11-30", "count": 99, "level": 4},  # outside the 12-month window
        {"date": "2025-12-05", "count": 3, "level": 1},
        {"date": "2026-06-10", "count": 4, "level": 2},
        {"date": "2026-06-11", "count": 1, "level": 1},
        {"date": "2026-11-16", "count": 2, "level": 1},
    ]
    monthly = compute_activity(days, TODAY)["monthly"]
    assert len(monthly) == 12
    assert monthly[0] == {"month": "2025-12", "label": "Dec 2025", "total": 3}
    assert monthly[-1] == {"month": "2026-11", "label": "Nov 2026", "total": 2}
    assert {m["month"]: m["total"] for m in monthly}["2026-06"] == 5
    assert sum(m["total"] for m in monthly) == 10


def test_consistency_percentage() -> None:
    days = _days(TODAY - timedelta(days=9), [1, 0, 0, 2, 0, 0, 0, 3, 0, 0])
    activity = compute_activity(days, TODAY)
    assert activity["active_days"] == 3
    assert activity["consistency_percentage"] == 30.0
    assert activity["average_per_active_day"] == 2.0


@pytest.mark.parametrize(
    ("last", "previous", "direction", "change"),
    [(80, 60, "up", 33.3), (30, 60, "down", -50.0), (10, 10, "flat", 0.0), (5, 0, "up", None),
     (0, 0, "flat", None)],
)
def test_trend_directions(last: int, previous: int, direction: str, change: float | None) -> None:
    days = [
        {"date": TODAY.isoformat(), "count": last, "level": 1},
        {"date": (TODAY - timedelta(days=29)).isoformat(), "count": 0, "level": 0},
        {"date": (TODAY - timedelta(days=30)).isoformat(), "count": previous, "level": 1},
        {"date": (TODAY - timedelta(days=60)).isoformat(), "count": 1000, "level": 4},  # ignored
    ]
    trend = compute_activity(days, TODAY)["trend"]
    assert trend == {"last_30_days": last, "previous_30_days": previous,
                     "change_percentage": change, "direction": direction}


def test_empty_activity() -> None:
    activity = compute_activity([], TODAY)
    assert activity["active_days"] == 0 and activity["total_days"] == 0
    assert activity["consistency_percentage"] == 0.0
    assert activity["average_per_active_day"] == 0.0
    assert activity["most_active_weekday"] is None
    assert all(t["total"] == 0 and t["average"] == 0.0 for t in activity["weekday_totals"])
    assert len(activity["monthly"]) == 12
    assert activity["trend"] == {"last_30_days": 0, "previous_30_days": 0,
                                 "change_percentage": None, "direction": "flat"}


# ---------- readiness ----------

def _repo(name: str, stars: int = 0, *, full: bool = False, fork: bool = False,
          updated: str = "2026-11-01T00:00:00Z") -> dict[str, Any]:
    return {
        "id": hash(name) % 10_000, "name": name, "full_name": f"me/{name}", "html_url": f"https://g/{name}",
        "description": "A project" if full else None, "topics": ["python"] if full else [],
        "license": "MIT" if full else None, "homepage": "https://demo" if full else None,
        "archived": False, "open_issues": 0, "stars": stars, "forks": 0, "language": "Python",
        "updated_at": updated, "is_fork": fork,
    }


FULL_PROFILE = {"login": "me", "name": "Me", "bio": "Backend dev", "location": "Pune",
                "company": None, "blog": "https://me.dev"}


def _checks(readiness: dict[str, Any]) -> dict[str, bool]:
    return {c["id"]: c["passed"] for c in readiness["checks"]}


def test_perfect_profile_scores_100() -> None:
    portfolio = {"profile": FULL_PROFILE,
                 "repositories": [_repo(f"r{i}", stars=10 + i, full=True) for i in range(3)]}
    activity = compute_activity(_days(TODAY - timedelta(days=9), [1] * 10), TODAY)
    readiness = compute_readiness(portfolio, activity, TODAY)
    assert all(_checks(readiness).values())
    assert len(readiness["checks"]) == 10
    assert readiness["score"] == 100 and readiness["grade"] == "Excellent"
    assert readiness["recommendations"] == []
    assert [r["score"] for r in readiness["repositories"]] == [100, 100, 100]
    assert readiness["repositories"][0]["name"] == "r2"


def test_bare_profile_scores_low_and_names_repos() -> None:
    repos = [_repo(n, updated="2024-01-01T00:00:00Z") for n in ("alpha", "beta", "gamma", "delta")]
    portfolio = {"profile": {"login": "me"}, "repositories": repos}
    readiness = compute_readiness(portfolio, compute_activity([], TODAY), TODAY)
    assert readiness["score"] == 0 and readiness["grade"] == "Low"
    assert not any(_checks(readiness).values())
    recs = readiness["recommendations"]
    assert len(recs) == 10
    license_rec = next(r for r in recs if "license" in r.lower())
    assert "4 repositories" in license_rec and "alpha, beta, gamma" in license_rec
    assert "delta" not in license_rec
    assert readiness["repositories"][0]["score"] == 17  # only "not archived" passes
    assert "No license" in readiness["repositories"][0]["issues"]


def test_readiness_ignores_forks_and_handles_empty() -> None:
    empty = compute_readiness({"profile": {"login": "me"}, "repositories": []},
                              compute_activity([], TODAY), TODAY)
    assert empty["score"] == 0 and empty["repositories"] == []
    forked = compute_readiness(
        {"profile": FULL_PROFILE, "repositories": [_repo("fork", 50, full=True, fork=True)]},
        compute_activity([], TODAY), TODAY,
    )
    assert forked["repositories"] == []
    assert _checks(forked)["repo_descriptions"] is False


def test_partial_repo_coverage_thresholds() -> None:
    repos = [_repo(f"r{i}", full=i < 7) for i in range(10)]  # 70% described
    readiness = compute_readiness({"profile": FULL_PROFILE, "repositories": repos},
                                  compute_activity([], TODAY), TODAY)
    checks = _checks(readiness)
    assert checks["repo_descriptions"] and checks["repo_topics"] and checks["repo_licenses"]
    assert not checks["popular_project"] and not checks["consistency"]
    assert len(readiness["repositories"]) == 6


# ---------- migration / cache ----------

OLD_REPOSITORIES = """
CREATE TABLE repositories (
    id INTEGER PRIMARY KEY, username TEXT NOT NULL COLLATE NOCASE, name TEXT NOT NULL,
    full_name TEXT NOT NULL, description TEXT, html_url TEXT NOT NULL,
    stars INTEGER NOT NULL DEFAULT 0, forks INTEGER NOT NULL DEFAULT 0, language TEXT,
    topics TEXT NOT NULL DEFAULT '[]', updated_at TEXT, is_fork INTEGER NOT NULL DEFAULT 0,
    fetched_at REAL NOT NULL
);
"""


def test_init_db_migrates_old_repositories_table(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    db_path = tmp_path / "old.db"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(OLD_REPOSITORIES)
        conn.execute(
            "INSERT INTO repositories (id, username, name, full_name, html_url, fetched_at)"
            " VALUES (1, 'me', 'old', 'me/old', 'https://g/old', 0)"
        )
    monkeypatch.setattr(database, "settings", dataclasses.replace(settings, db_path=db_path))
    database.init_db()
    database.init_db()  # idempotent
    with sqlite3.connect(db_path) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(repositories)")}
        row = conn.execute("SELECT license, homepage, archived, open_issues FROM repositories").fetchone()
    assert {"license", "homepage", "archived", "open_issues"} <= columns
    assert row == (None, None, 0, 0)


def test_old_cached_rows_load_with_defaults() -> None:
    cache_repository.save_snapshot("me", {"login": "me"}, [_repo("new", full=True)], [], "graphql", 1.0)
    with database.get_connection() as conn:
        conn.execute(
            "INSERT INTO repositories (id, username, name, full_name, html_url, fetched_at)"
            " VALUES (999, 'me', 'legacy', 'me/legacy', 'https://g/legacy', 1.0)"
        )
    repos = {r["name"]: r for r in cache_repository.load_snapshot("me")["repositories"]}
    assert repos["legacy"]["license"] is None and repos["legacy"]["homepage"] is None
    assert repos["legacy"]["archived"] is False and repos["legacy"]["open_issues"] == 0
    assert repos["new"]["license"] == "MIT" and repos["new"]["homepage"] == "https://demo"


@pytest.mark.parametrize(
    ("raw_license", "expected"),
    [({"spdx_id": "MIT", "name": "MIT License"}, "MIT"),
     ({"spdx_id": "NOASSERTION", "name": "Other"}, "Other"),
     (None, None)],
)
def test_normalize_repository_new_fields(raw_license: dict[str, str] | None, expected: str | None) -> None:
    repo = portfolio_service.normalize_repository({
        "id": 1, "name": "x", "full_name": "me/x", "html_url": "https://g/x", "license": raw_license,
        "homepage": "", "archived": True, "open_issues_count": 3,
    })
    assert repo["license"] == expected
    assert repo["homepage"] is None and repo["archived"] is True and repo["open_issues"] == 3


# ---------- endpoint ----------

def test_insights_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, bool]] = []
    days = _days(TODAY - timedelta(days=6), [1, 0, 2, 0, 3, 0, 4])

    def fake_get_portfolio(username: str, refresh: bool = False) -> dict[str, Any]:
        calls.append((username, refresh))
        return {"profile": FULL_PROFILE, "repositories": [_repo("api", 7, full=True)],
                "contributions": {"weeks": [days[:3], days[3:]]}}

    monkeypatch.setattr(portfolio_service, "get_portfolio", fake_get_portfolio)
    with TestClient(app) as client:
        response = client.get("/api/insights/me?refresh=true")
        invalid = client.get("/api/insights/-bad-")
    assert response.status_code == 200
    assert calls == [("me", True)]
    body = response.json()
    assert body["activity"]["active_days"] == 4 and body["activity"]["total_days"] == 7
    assert len(body["activity"]["weekday_totals"]) == 7
    assert body["readiness"]["grade"] in {"Excellent", "Strong", "Moderate", "Low"}
    assert body["readiness"]["repositories"][0]["name"] == "api"
    assert invalid.status_code == 422
    assert insights_service.portfolio_service is portfolio_service
