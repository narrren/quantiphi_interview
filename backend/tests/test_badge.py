"""Tests for SVG badge rendering and GET /api/badge/{username} (no network)."""
from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.errors import GitHubUserNotFound
from app.services import portfolio_service
from app.services.badge_service import badge_for, compact_number, render_badge
from tests._v2_app import build_app

SVG_NS = "{http://www.w3.org/2000/svg}"

PORTFOLIO: dict[str, Any] = {
    "profile": {"login": "octocat", "followers": 1500},
    "stats": {
        "total_stars": 268180,
        "top_languages": [
            {"name": "Other", "count": 9, "percentage": 50.0, "color": "#8b949e"},
            {"name": "Python", "count": 5, "percentage": 30.0, "color": "#3572A5"},
        ],
    },
    "contributions": {"total": 999, "current_streak": 2, "longest_streak": 104},
}


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "0"), (999, "999"), (1000, "1K"), (1234, "1.2K"), (268180, "268.2K"),
        (999950, "1M"), (1_000_000, "1M"), (2_500_000, "2.5M"), (12_340_000, "12.3M"),
    ],
)
def test_compact_number(value: int, expected: str) -> None:
    assert compact_number(value) == expected


def test_render_badge_is_valid_svg_with_accessibility() -> None:
    svg = render_badge("GitHub stars", "268.2K", "#dfb317")
    root = ET.fromstring(svg)
    assert root.tag == f"{SVG_NS}svg"
    assert root.get("role") == "img"
    assert root.get("aria-label") == "GitHub stars: 268.2K"
    assert root.find(f"{SVG_NS}title").text == "GitHub stars: 268.2K"
    assert root.find(f"{SVG_NS}clipPath") is not None
    texts = [t.text for t in root.iter(f"{SVG_NS}text")]
    assert texts == ["GitHub stars", "GitHub stars", "268.2K", "268.2K"]
    assert int(root.get("width")) > 0 and root.get("height") == "20"
    assert any(r.get("fill") == "#dfb317" for r in root.iter(f"{SVG_NS}rect"))


def test_render_badge_width_grows_with_text() -> None:
    short = ET.fromstring(render_badge("a", "1", "#000"))
    long = ET.fromstring(render_badge("a much longer label", "1", "#000"))
    assert int(long.get("width")) > int(short.get("width"))


def test_render_badge_escapes_xml() -> None:
    svg = render_badge('<label & "x">', "<&>", "#000")
    assert "<&>" not in svg
    root = ET.fromstring(svg)
    assert root.get("aria-label") == '<label & "x">: <&>'
    texts = [t.text for t in root.iter(f"{SVG_NS}text")]
    assert texts[0] == '<label & "x">' and texts[2] == "<&>"


@pytest.mark.parametrize(
    ("metric", "expected"),
    [
        ("stars", ("GitHub stars", "268.2K", "#dfb317")),
        ("followers", ("followers", "1.5K", "#2f81f7")),
        ("contributions", ("contributions (1y)", "999", "#2ea043")),
        ("streak", ("longest streak", "104 days", "#f0883e")),
        ("top_language", ("top language", "Python", "#3572A5")),
    ],
)
def test_badge_for_metrics(metric: str, expected: tuple[str, str, str]) -> None:
    assert badge_for(PORTFOLIO, metric) == expected


def test_badge_for_top_language_missing() -> None:
    empty = {"profile": {"login": "x"}, "stats": {"top_languages": []}, "contributions": {}}
    assert badge_for(empty, "top_language") == ("top language", "n/a", "#8b949e")


# --- endpoint -----------------------------------------------------------------------


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    def fake_get_portfolio(username: str, refresh: bool = False) -> dict[str, Any]:
        if username != "octocat":
            raise GitHubUserNotFound(f"GitHub user '{username}' not found")
        return PORTFOLIO

    monkeypatch.setattr(portfolio_service, "get_portfolio", fake_get_portfolio)
    return TestClient(build_app())


def test_badge_endpoint_default_stars(client: TestClient) -> None:
    res = client.get("/api/badge/octocat")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("image/svg+xml")
    assert res.headers["cache-control"] == "public, max-age=3600"
    root = ET.fromstring(res.text)
    assert root.get("aria-label") == "GitHub stars: 268.2K"


def test_badge_endpoint_metric(client: TestClient) -> None:
    res = client.get("/api/badge/octocat", params={"metric": "streak", "style": "flat"})
    assert res.status_code == 200
    assert ET.fromstring(res.text).get("aria-label") == "longest streak: 104 days"


def test_badge_endpoint_unknown_metric(client: TestClient) -> None:
    assert client.get("/api/badge/octocat", params={"metric": "nope"}).status_code == 422


def test_badge_endpoint_invalid_username(client: TestClient) -> None:
    assert client.get("/api/badge/bad_name!").status_code == 422


def test_badge_endpoint_user_not_found_is_json(client: TestClient) -> None:
    res = client.get("/api/badge/ghost")
    assert res.status_code == 404
    assert res.headers["content-type"].startswith("application/json")
    assert "ghost" in res.json()["detail"]
