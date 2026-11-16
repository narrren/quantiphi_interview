"""Tests for portfolio aggregation, caching behaviour, settings and the HTTP layer (no network)."""
from __future__ import annotations

from typing import Any

import pytest
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from app.core.errors import AppError, GitHubRateLimited, GitHubUserNotFound, UpstreamError
from app.routers import portfolio, user_settings
from app.services import portfolio_service
from app.services.settings_service import get_settings, update_settings

LANGS = ["Python", "Python", "Python", "TypeScript", "TypeScript", "Go", "Rust", "C", "Java", "Zig", None]


def _raw_repo(i: int, language: str | None, stars: int, fork: bool = False, updated: str = "2026-01-01T00:00:00Z") -> dict[str, Any]:
    return {
        "id": i, "name": f"repo-{i}", "full_name": f"octocat/repo-{i}", "description": None,
        "html_url": f"https://github.com/octocat/repo-{i}", "stargazers_count": stars,
        "forks_count": 1, "language": language, "topics": ["api"], "updated_at": updated, "fork": fork,
    }


RAW_USER = {
    "login": "octocat", "name": "The Octocat", "avatar_url": "https://a", "bio": None,
    "company": "@github", "location": "SF", "blog": "", "html_url": "https://github.com/octocat",
    "followers": 10, "following": 2, "public_repos": 13, "created_at": "2011-01-25T18:44:36Z",
}
RAW_REPOS = [_raw_repo(i, lang, stars=i) for i, lang in enumerate(LANGS, start=1)] + [
    _raw_repo(100, "Python", stars=500, fork=True),
    _raw_repo(101, "Elixir", stars=0, updated="2026-06-01T00:00:00Z"),
    _raw_repo(102, None, stars=0, updated="2025-06-01T00:00:00Z"),
]
DAYS = [{"date": "2026-11-15", "count": 3, "level": 2}, {"date": "2026-11-16", "count": 1, "level": 1}]


class FakeGitHub:
    """Records calls and optionally raises, standing in for the network layer."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.calls = 0
        self.error: AppError | None = None
        monkeypatch.setattr(portfolio_service.github_client, "fetch_user", self.fetch_user)
        monkeypatch.setattr(portfolio_service.github_client, "fetch_repositories", lambda _: RAW_REPOS)
        monkeypatch.setattr(
            portfolio_service.contributions, "fetch_contribution_days", lambda *_, **__: (DAYS, "scrape")
        )

    def fetch_user(self, username: str) -> dict[str, Any]:
        self.calls += 1
        if self.error:
            raise self.error
        return RAW_USER


@pytest.fixture
def github(monkeypatch: pytest.MonkeyPatch) -> FakeGitHub:
    return FakeGitHub(monkeypatch)


def test_stats_and_top_languages(github: FakeGitHub) -> None:
    result = portfolio_service.get_portfolio("octocat")
    stats = result["stats"]
    # Forked repo (500 stars) is excluded from the totals.
    assert stats["total_stars"] == sum(range(1, 12))
    assert stats["total_forks"] == 13
    assert stats["total_repos"] == 14
    langs = stats["top_languages"]
    assert [(l["name"], l["count"]) for l in langs] == [
        ("Python", 3), ("TypeScript", 2), ("C", 1), ("Elixir", 1), ("Go", 1), ("Java", 1), ("Other", 2),
    ]
    assert langs[0] == {"name": "Python", "count": 3, "percentage": 27.3, "color": "#3572A5"}
    assert langs[-1]["color"] == "#8b949e"
    assert abs(sum(l["percentage"] for l in langs) - 100) < 0.5


def test_repositories_sorted_and_enriched(github: FakeGitHub) -> None:
    repos = portfolio_service.get_portfolio("octocat")["repositories"]
    assert repos[-1]["is_fork"] is True
    assert [r["stars"] for r in repos[:-1]] == sorted((r["stars"] for r in repos[:-1]), reverse=True)
    # Equal stars (0) -> most recently updated first.
    assert [r["id"] for r in repos[-3:-1]] == [101, 102]
    colors = {r["language"]: r["language_color"] for r in repos}
    assert colors["Python"] == "#3572A5" and colors[None] is None
    assert set(repos[0]) == {
        "id", "name", "full_name", "description", "html_url", "stars", "forks",
        "language", "language_color", "topics", "updated_at", "is_fork",
    }


def test_profile_and_contributions_shape(github: FakeGitHub) -> None:
    result = portfolio_service.get_portfolio("octocat")
    assert result["profile"]["login"] == "octocat" and result["profile"]["blog"] is None
    contrib = result["contributions"]
    assert contrib["total"] == 4 and contrib["source"] == "scrape"
    assert contrib["best_day"] == {"date": "2026-11-15", "count": 3}
    assert sum(len(w) for w in contrib["weeks"]) == 2


def test_cache_hit_refresh_and_case_insensitivity(github: FakeGitHub) -> None:
    first = portfolio_service.get_portfolio("octocat")
    assert first["cache"]["cached"] is False and github.calls == 1
    second = portfolio_service.get_portfolio("OctoCat")
    assert second["cache"]["cached"] is True and github.calls == 1
    assert second["stats"] == first["stats"]
    assert second["repositories"] == first["repositories"]
    assert second["cache"]["fetched_at"].endswith("+00:00")
    third = portfolio_service.get_portfolio("octocat", refresh=True)
    assert third["cache"]["cached"] is False and github.calls == 2


@pytest.mark.parametrize("error", [GitHubRateLimited("rl"), UpstreamError("down")])
def test_stale_cache_served_on_upstream_failure(github: FakeGitHub, error: AppError) -> None:
    portfolio_service.get_portfolio("octocat")
    github.error = error
    result = portfolio_service.get_portfolio("octocat", refresh=True)
    assert result["cache"] == {**result["cache"], "cached": True, "stale": True}


@pytest.mark.parametrize("error", [GitHubRateLimited("rl"), UpstreamError("down"), GitHubUserNotFound("nf")])
def test_errors_propagate_without_cache(github: FakeGitHub, error: AppError) -> None:
    github.error = error
    with pytest.raises(type(error)):
        portfolio_service.get_portfolio("octocat")


def test_user_not_found_propagates_even_with_cache(github: FakeGitHub) -> None:
    portfolio_service.get_portfolio("octocat")
    github.error = GitHubUserNotFound("nf")
    with pytest.raises(GitHubUserNotFound):
        portfolio_service.get_portfolio("octocat", refresh=True)


def test_settings_defaults_and_partial_update() -> None:
    assert get_settings() == {
        "default_username": "", "theme": "dark", "cache_ttl_seconds": 3600, "last_job_description": "",
    }
    updated = update_settings({"last_job_description": "Python dev", "unknown": 1})
    assert updated["last_job_description"] == "Python dev" and updated["theme"] == "dark"
    assert update_settings({"theme": "light"})["last_job_description"] == "Python dev"


def _client() -> TestClient:
    app = FastAPI()

    @app.exception_handler(AppError)
    async def handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(portfolio.router, prefix="/api")
    app.include_router(user_settings.router, prefix="/api")
    return TestClient(app)


def test_http_portfolio_validation_and_errors(github: FakeGitHub) -> None:
    client = _client()
    assert client.get("/api/portfolio/-bad").status_code == 422
    assert client.get("/api/portfolio/octocat").json()["profile"]["login"] == "octocat"
    github.error = GitHubUserNotFound("GitHub user not found")
    response = client.get("/api/portfolio/ghost", params={"refresh": True})
    assert response.status_code == 404 and response.json() == {"detail": "GitHub user not found"}


@pytest.mark.parametrize(
    "body",
    [{"theme": "blue"}, {"cache_ttl_seconds": 59}, {"cache_ttl_seconds": 86401},
     {"default_username": "-bad"}, {"last_job_description": "x" * 20001}],
)
def test_http_settings_validation(body: dict[str, Any]) -> None:
    assert _client().put("/api/settings", json=body).status_code == 422


def test_http_settings_roundtrip() -> None:
    client = _client()
    response = client.put("/api/settings", json={"default_username": "octocat", "cache_ttl_seconds": 120})
    assert response.status_code == 200
    assert client.get("/api/settings").json() == {
        "default_username": "octocat", "theme": "dark", "cache_ttl_seconds": 120, "last_job_description": "",
    }
    assert client.put("/api/settings", json={"default_username": ""}).json()["default_username"] == ""
