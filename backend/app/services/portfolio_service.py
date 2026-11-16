"""Portfolio aggregation with SQLite-backed caching (the core business logic)."""
from __future__ import annotations

import logging
import time
from collections import Counter
from datetime import UTC, datetime
from typing import Any

from app.core.config import settings as app_config
from app.core.errors import GitHubRateLimited, UpstreamError
from app.repositories import cache_repository
from app.services import contributions, github_client
from app.services.settings_service import get_settings

logger = logging.getLogger(__name__)

TOP_LANGUAGES_LIMIT = 6
OTHER_LANGUAGE = "Other"
DEFAULT_LANGUAGE_COLOR = "#8b949e"

# Subset of GitHub linguist colors for common languages.
LANGUAGE_COLORS: dict[str, str] = {
    "Python": "#3572A5", "JavaScript": "#f1e05a", "TypeScript": "#3178c6",
    "Java": "#b07219", "C": "#555555", "C++": "#f34b7d", "C#": "#178600",
    "Go": "#00ADD8", "Rust": "#dea584", "Ruby": "#701516", "PHP": "#4F5D95",
    "Swift": "#F05138", "Kotlin": "#A97BFF", "Dart": "#00B4AB", "Scala": "#c22d40",
    "Shell": "#89e051", "PowerShell": "#012456", "HTML": "#e34c26", "CSS": "#663399",
    "SCSS": "#c6538c", "Vue": "#41b883", "Svelte": "#ff3e00", "Jupyter Notebook": "#DA5B0B",
    "R": "#198CE7", "Lua": "#000080", "Perl": "#0298c3", "Haskell": "#5e5086",
    "Elixir": "#6e4a7e", "Erlang": "#B83998", "Clojure": "#db5855", "Objective-C": "#438eff",
    "Julia": "#a270ba", "MATLAB": "#e16737", "Groovy": "#4298b8", "Dockerfile": "#384d54",
    "Makefile": "#427819", "HCL": "#844FBA", "Vim Script": "#199f4b", "Zig": "#ec915c",
    "OCaml": "#ef7a08", "F#": "#b845fc", "Solidity": "#AA6746", "Nix": "#7e7eff",
    "TeX": "#3D6117", "Assembly": "#6E4C13", "CoffeeScript": "#244776", "Elm": "#60B5CC",
}


def language_color(language: str | None) -> str | None:
    """Return the display color for a language (None when the repo has no language)."""
    if language is None:
        return None
    return LANGUAGE_COLORS.get(language, DEFAULT_LANGUAGE_COLOR)


def normalize_profile(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a raw GitHub user object to the contract's `profile` shape."""
    return {
        "login": raw["login"],
        "name": raw.get("name") or None,
        "avatar_url": raw.get("avatar_url") or None,
        "bio": raw.get("bio") or None,
        "company": raw.get("company") or None,
        "location": raw.get("location") or None,
        "blog": raw.get("blog") or None,
        "html_url": raw.get("html_url") or f"https://github.com/{raw['login']}",
        "followers": int(raw.get("followers") or 0),
        "following": int(raw.get("following") or 0),
        "public_repos": int(raw.get("public_repos") or 0),
        "created_at": raw.get("created_at"),
    }


def normalize_repository(raw: dict[str, Any]) -> dict[str, Any]:
    """Map a raw GitHub repository object to the stored repository shape."""
    return {
        "id": int(raw["id"]),
        "name": raw["name"],
        "full_name": raw["full_name"],
        "description": raw.get("description"),
        "html_url": raw["html_url"],
        "stars": int(raw.get("stargazers_count") or 0),
        "forks": int(raw.get("forks_count") or 0),
        "language": raw.get("language"),
        "topics": list(raw.get("topics") or []),
        "updated_at": raw.get("updated_at"),
        "is_fork": bool(raw.get("fork")),
    }


def sort_repositories(repositories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Non-forks first, then stars desc, then updated_at desc."""
    by_recency = sorted(repositories, key=lambda r: r["updated_at"] or "", reverse=True)
    return sorted(by_recency, key=lambda r: (r["is_fork"], -r["stars"]))


def compute_top_languages(repositories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Top languages by number of non-fork repos; the tail beyond the top 6 becomes "Other"."""
    counts = Counter(r["language"] for r in repositories if not r["is_fork"] and r["language"])
    total = sum(counts.values())
    if total == 0:
        return []
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
    top = [(name, count, language_color(name)) for name, count in ranked[:TOP_LANGUAGES_LIMIT]]
    rest = sum(count for _, count in ranked[TOP_LANGUAGES_LIMIT:])
    if rest:
        top.append((OTHER_LANGUAGE, rest, DEFAULT_LANGUAGE_COLOR))
    return [
        {"name": name, "count": count, "percentage": round(count * 100 / total, 1), "color": color}
        for name, count, color in top
    ]


def compute_stats(repositories: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate stars/forks over non-fork repos plus language distribution."""
    owned = [r for r in repositories if not r["is_fork"]]
    return {
        "total_stars": sum(r["stars"] for r in owned),
        "total_forks": sum(r["forks"] for r in owned),
        "total_repos": len(repositories),
        "top_languages": compute_top_languages(repositories),
    }


def _build_response(
    snapshot: dict[str, Any], *, cached: bool, stale: bool, ttl: int
) -> dict[str, Any]:
    repositories = [
        {**repo, "language_color": language_color(repo["language"])}
        for repo in sort_repositories(snapshot["repositories"])
    ]
    fetched_at = datetime.fromtimestamp(snapshot["fetched_at"], UTC)
    return {
        "profile": snapshot["profile"],
        "stats": compute_stats(snapshot["repositories"]),
        "repositories": repositories,
        "contributions": contributions.summarize(
            snapshot["days"], snapshot["source"], datetime.now(UTC).date()
        ),
        "cache": {
            "cached": cached,
            "fetched_at": fetched_at.isoformat(timespec="seconds"),
            "ttl_seconds": ttl,
            "stale": stale,
        },
    }


def _fetch_snapshot(username: str, previous: dict[str, Any] | None) -> dict[str, Any]:
    """Fetch fresh data from GitHub and persist it. Keeps the previously cached calendar
    if the contribution calendar is unavailable this time."""
    profile = normalize_profile(github_client.fetch_user(username))
    login = profile["login"]
    repositories = [normalize_repository(r) for r in github_client.fetch_repositories(login)]
    days, source = contributions.fetch_contribution_days(
        login, use_graphql=bool(app_config.github_token)
    )
    if source == "unavailable" and previous and previous["days"]:
        days, source = previous["days"], previous["source"]
    snapshot = {
        "profile": profile,
        "repositories": repositories,
        "days": days,
        "source": source,
        "fetched_at": time.time(),
    }
    cache_repository.save_snapshot(
        login, profile, repositories, days, source, snapshot["fetched_at"]
    )
    return snapshot


def get_portfolio(username: str, refresh: bool = False) -> dict[str, Any]:
    """Return the full portfolio for `username`, served from cache when fresh.

    Raises GitHubUserNotFound, or GitHubRateLimited/UpstreamError when GitHub fails
    and nothing is cached.
    """
    ttl = int(get_settings()["cache_ttl_seconds"])
    cached = cache_repository.load_snapshot(username)
    if cached and not refresh and time.time() - cached["fetched_at"] < ttl:
        return _build_response(cached, cached=True, stale=False, ttl=ttl)
    try:
        fresh = _fetch_snapshot(username, cached)
    except (GitHubRateLimited, UpstreamError) as exc:
        if cached is None:
            raise
        logger.warning("Serving stale cache for %s: %s", username, exc.message)
        return _build_response(cached, cached=True, stale=True, ttl=ttl)
    return _build_response(fresh, cached=False, stale=False, ttl=ttl)
