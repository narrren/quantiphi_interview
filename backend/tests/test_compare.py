"""Tests for the developer comparison logic and GET /api/compare (no network)."""
from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.errors import GitHubUserNotFound
from app.services import portfolio_service
from app.services.compare_service import METRICS, compare_developers
from tests._v2_app import build_app


def _portfolio(
    login: str,
    *,
    followers: int = 0,
    stars: int = 0,
    forks: int = 0,
    repos: int = 0,
    total: int = 0,
    current: int = 0,
    longest: int = 0,
    languages: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "profile": {
            "login": login,
            "name": login.title(),
            "avatar_url": f"https://avatars.example/{login}",
            "html_url": f"https://github.com/{login}",
            "followers": followers,
        },
        "stats": {
            "total_stars": stars,
            "total_forks": forks,
            "total_repos": repos,
            "top_languages": [
                {"name": n, "count": 1, "percentage": 10.0, "color": "#123456"} for n in languages
            ],
        },
        "contributions": {"total": total, "current_streak": current, "longest_streak": longest},
    }


ALICE = _portfolio(
    "alice", followers=10, stars=50, forks=5, repos=12, total=900, current=3, longest=20,
    languages=("Python", "Go", "Other"),
)
BOB = _portfolio(
    "bob", followers=20, stars=80, forks=5, repos=30, total=400, current=7, longest=20,
    languages=("Other", "TypeScript", "Python", "Go"),
)


def test_metrics_order_values_and_leaders() -> None:
    result = compare_developers([ALICE, BOB])
    assert [m["key"] for m in result["metrics"]] == [k for k, _ in METRICS]
    assert [m["key"] for m in result["metrics"]] == [
        "followers", "total_stars", "total_forks", "total_repos",
        "total_contributions", "current_streak", "longest_streak",
    ]
    leaders = {m["key"]: m["leader"] for m in result["metrics"]}
    assert leaders == {
        "followers": "bob",
        "total_stars": "bob",
        "total_forks": None,
        "total_repos": "bob",
        "total_contributions": "alice",
        "current_streak": "bob",
        "longest_streak": None,
    }
    assert result["metrics"][0]["values"] == [10, 20]
    assert result["summary"] == "bob leads in 4 of 7 metrics."


def test_developers_and_top_language_skip_other() -> None:
    result = compare_developers([ALICE, BOB])
    alice, bob = result["developers"]
    assert alice["login"] == "alice" and alice["top_language"] == "Python"
    assert bob["top_language"] == "TypeScript"
    assert alice["total_contributions"] == 900 and bob["current_streak"] == 7
    assert alice["html_url"] == "https://github.com/alice"


def test_top_language_null_when_none_or_only_other() -> None:
    empty = _portfolio("carol")
    other = _portfolio("dave", languages=("Other",))
    result = compare_developers([empty, other])
    assert [d["top_language"] for d in result["developers"]] == [None, None]
    assert result["shared_languages"] == []


def test_shared_languages_sorted_and_exclude_other() -> None:
    assert compare_developers([ALICE, BOB])["shared_languages"] == ["Go", "Python"]


def test_summary_even_and_all_tied() -> None:
    a = _portfolio("alice", followers=5, stars=5, forks=5)
    b = _portfolio("bob", repos=5, total=5, current=5)
    assert compare_developers([a, b])["summary"] == "alice and bob are evenly matched (3–3)."
    tied = compare_developers([_portfolio("x"), _portfolio("y")])
    assert all(m["leader"] is None for m in tied["metrics"])
    assert tied["summary"] == "x and y are evenly matched (0–0)."


def test_summary_first_developer_leads() -> None:
    a = _portfolio("alice", followers=9, stars=9, forks=9, repos=9, total=9, current=9, longest=9)
    assert compare_developers([a, _portfolio("bob")])["summary"] == "alice leads in 7 of 7 metrics."


def test_requires_exactly_two() -> None:
    with pytest.raises(ValueError):
        compare_developers([ALICE])


# --- endpoint -----------------------------------------------------------------------


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    data = {"alice": ALICE, "bob": BOB}

    def fake_get_portfolio(username: str, refresh: bool = False) -> dict[str, Any]:
        if username.lower() not in data:
            raise GitHubUserNotFound(f"GitHub user '{username}' not found")
        return data[username.lower()]

    monkeypatch.setattr(portfolio_service, "get_portfolio", fake_get_portfolio)
    return TestClient(build_app())


def test_compare_endpoint_ok(client: TestClient) -> None:
    res = client.get("/api/compare", params={"users": " alice , bob "})
    assert res.status_code == 200
    body = res.json()
    assert [d["login"] for d in body["developers"]] == ["alice", "bob"]
    assert len(body["metrics"]) == 7
    assert body["metrics"][0] == {
        "key": "followers", "label": "Followers", "values": [10, 20], "leader": "bob",
    }
    assert body["shared_languages"] == ["Go", "Python"]
    assert body["summary"] == "bob leads in 4 of 7 metrics."


@pytest.mark.parametrize(
    "users",
    ["alice", "alice,bob,carol", "alice,ALICE", "alice,", ",bob", "alice,bad_name!", "alice,-bob", ""],
)
def test_compare_endpoint_rejects_invalid(client: TestClient, users: str) -> None:
    res = client.get("/api/compare", params={"users": users})
    assert res.status_code == 422
    assert res.json()["detail"]


def test_compare_endpoint_missing_param(client: TestClient) -> None:
    assert client.get("/api/compare").status_code == 422


def test_compare_endpoint_user_not_found(client: TestClient) -> None:
    res = client.get("/api/compare", params={"users": "alice,ghost"})
    assert res.status_code == 404
    assert "ghost" in res.json()["detail"]
