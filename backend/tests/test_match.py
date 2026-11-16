"""Tests for the tech taxonomy, the match scoring engine and POST /api/match (no network)."""
from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.core.errors import GitHubUserNotFound
from app.main import app
from app.services import portfolio_service, settings_service
from app.services.match_service import MAX_EVIDENCE, compute_match, grade_for
from app.services.tech_keywords import TECH_BY_NAME, extract_technologies


def _repo(name: str, language: str | None, stars: int = 0, **extra: Any) -> dict[str, Any]:
    return {
        "name": name,
        "description": extra.get("description"),
        "html_url": f"https://github.com/octocat/{name}",
        "stars": stars,
        "forks": 0,
        "language": language,
        "topics": extra.get("topics", []),
        "updated_at": "2026-01-01T00:00:00Z",
        "is_fork": extra.get("is_fork", False),
    }


@pytest.fixture
def portfolio() -> dict[str, Any]:
    return {
        "profile": {"login": "octocat", "name": "The Octocat", "followers": 10, "following": 2},
        "stats": {"total_stars": 190, "total_forks": 0, "total_repos": 5, "top_languages": []},
        "repositories": [
            _repo("k8s-fork", "Go", 100, topics=["kubernetes"], is_fork=True),
            _repo("api-server", "Python", 50, topics=["fastapi", "docker"]),
            _repo("web-dashboard", "TypeScript", 30, description="Dashboard built with React and Redis"),
            _repo("go-utils", "Go", 10),
            _repo("notes", None, 0, description="Thoughts on learning Rust"),
        ],
        "contributions": {"total": 0, "current_streak": 0, "longest_streak": 0, "best_day": None},
    }


def _names(text: str) -> list[str]:
    return [tech.name for tech in extract_technologies(text)]


# --- taxonomy / extraction -------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Strong golang background", ["Go"]),
        ("We build services in Go.", ["Go"]),
        ("Go developers and React engineers wanted", ["Go", "React"]),
        ("Strong Go and Rust; we use Go for microservices", ["Go", "Rust"]),
        ("Frontend with ReactJS and react.js", ["React"]),
        ("Modern C++ (cpp) and C# experience", ["C++", "C#"]),
        ("Backend on .NET and ASP.NET", ["C#"]),
        ("Embedded C and C/C++ code", ["C", "C++"]),
        ("Statistics in R preferred", ["R"]),
        ("Deploy to k8s on AWS", ["Kubernetes", "AWS"]),
        ("Node.js and Next.js apps", ["Node.js", "Next.js"]),
        ("Spring Boot microservices in Java", ["Spring", "Java"]),
    ],
)
def test_aliases_resolve_to_canonical_names(text: str, expected: list[str]) -> None:
    assert _names(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "A good team player who is good to go",
        "Be the go-to person for the team",
        "Partner with R&D and C-level executives",
        "Engineers must react quickly, deliver swift results and plan for spring hiring",
        "Excellent communication skills and a cargo of goodwill",
        "Go above and beyond. React quickly to incidents. Spring internship available.",
    ],
)
def test_no_false_positives(text: str) -> None:
    assert _names(text) == []


def test_javascript_does_not_imply_java_and_keywords_are_deduped_in_order() -> None:
    assert _names("JavaScript, TypeScript, then JavaScript again, js and ts") == ["JavaScript", "TypeScript"]


def test_identifier_matching_handles_separators() -> None:
    assert TECH_BY_NAME["React"].in_identifier("my-react-app")
    assert TECH_BY_NAME["Go"].in_identifier("go_utils")
    assert TECH_BY_NAME["scikit-learn"].in_identifier("scikit-learn")
    assert not TECH_BY_NAME["Go"].in_identifier("google-maps")


# --- scoring -------------------------------------------------------------------------------


def test_weighted_percentage_and_evidence(portfolio: dict[str, Any]) -> None:
    jd = "Looking for Python and Rust engineers with Docker and Kubernetes experience."
    result = compute_match(portfolio, jd)

    # Python (lang, 2) + Docker (tool, 1) matched; Rust (lang, 2) + Kubernetes (tool, 1) missing → 3/6.
    assert result["match_percentage"] == 50
    assert result["grade"] == "Moderate"
    assert result["jd_keywords_count"] == 4
    assert result["matched"] == [
        {"keyword": "Python", "category": "language", "evidence": ["api-server"]},
        {"keyword": "Docker", "category": "tool", "evidence": ["api-server"]},
    ]
    # Rust appears only in a description (languages need primary-language/topic evidence);
    # Kubernetes appears only in a fork.
    assert result["missing"] == [
        {"keyword": "Rust", "category": "language"},
        {"keyword": "Kubernetes", "category": "tool"},
    ]
    assert result["summary"] == "2 of 4 technologies in the job description appear in octocat's repositories."


def test_frameworks_match_via_language_and_description(portfolio: dict[str, Any]) -> None:
    result = compute_match(portfolio, "Need React, Redis, FastAPI and golang skills for this role")
    evidence = {m["keyword"]: m["evidence"] for m in result["matched"]}
    assert evidence == {
        "React": ["web-dashboard"],
        "Redis": ["web-dashboard"],
        "FastAPI": ["api-server"],
        "Go": ["go-utils"],
    }
    assert result["match_percentage"] == 100
    assert result["grade"] == "Excellent"
    assert result["missing"] == []


def test_forks_are_not_evidence(portfolio: dict[str, Any]) -> None:
    result = compute_match(portfolio, "Must know Go well, plus Kubernetes operators")
    assert result["matched"] == [{"keyword": "Go", "category": "language", "evidence": ["go-utils"]}]
    assert result["missing"] == [{"keyword": "Kubernetes", "category": "tool"}]
    assert result["match_percentage"] == 67  # 2 of 3 weighted points


def test_evidence_capped_and_sorted_by_stars(portfolio: dict[str, Any]) -> None:
    portfolio["repositories"] = [_repo(f"py-{i}", "Python", stars=i) for i in range(8)]
    result = compute_match(portfolio, "Senior Python developer wanted for our team")
    assert result["matched"][0]["evidence"] == ["py-7", "py-6", "py-5", "py-4", "py-3"]
    assert len(result["matched"][0]["evidence"]) == MAX_EVIDENCE


def test_no_known_keywords(portfolio: dict[str, Any]) -> None:
    result = compute_match(portfolio, "We value teamwork, ownership and great communication.")
    assert result["match_percentage"] == 0
    assert result["grade"] == "Low"
    assert result["matched"] == result["missing"] == []
    assert result["jd_keywords_count"] == 0
    assert "No recognizable technologies" in result["summary"]


def test_empty_portfolio_scores_zero(portfolio: dict[str, Any]) -> None:
    portfolio["repositories"] = []
    result = compute_match(portfolio, "Python and Docker engineer needed")
    assert result["match_percentage"] == 0
    assert [m["keyword"] for m in result["missing"]] == ["Python", "Docker"]


@pytest.mark.parametrize(
    ("percentage", "grade"),
    [(100, "Excellent"), (80, "Excellent"), (79, "Strong"), (60, "Strong"), (59, "Moderate"), (40, "Moderate"),
     (39, "Low"), (0, "Low")],
)
def test_grade_thresholds(percentage: int, grade: str) -> None:
    assert grade_for(percentage) == grade


# --- router --------------------------------------------------------------------------------


@pytest.fixture
def client(portfolio: dict[str, Any], monkeypatch: pytest.MonkeyPatch) -> TestClient:
    def fake_get_portfolio(username: str, refresh: bool = False) -> dict[str, Any]:
        if username == "ghost":
            raise GitHubUserNotFound("GitHub user 'ghost' not found")
        return portfolio

    monkeypatch.setattr(portfolio_service, "get_portfolio", fake_get_portfolio)
    return TestClient(app)


def test_match_endpoint_scores_and_saves_last_jd(client: TestClient) -> None:
    jd = "  Python and Docker engineer for our platform team  "
    response = client.post("/api/match", json={"username": "octocat", "job_description": jd})
    assert response.status_code == 200
    body = response.json()
    assert body["match_percentage"] == 100
    assert body["jd_keywords_count"] == 2
    assert settings_service.get_settings()["last_job_description"] == jd.strip()


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "octocat", "job_description": "too short"},
        {"username": "octocat", "job_description": "x" * 20001},
        {"username": "-bad-name", "job_description": "Python and Docker engineer wanted"},
        {"username": "octocat"},
    ],
)
def test_match_endpoint_validation(client: TestClient, payload: dict[str, Any]) -> None:
    assert client.post("/api/match", json=payload).status_code == 422


def test_match_endpoint_unknown_user(client: TestClient) -> None:
    response = client.post("/api/match", json={"username": "ghost", "job_description": "Python and Docker engineer"})
    assert response.status_code == 404
    assert response.json() == {"detail": "GitHub user 'ghost' not found"}
