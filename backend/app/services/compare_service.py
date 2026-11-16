"""Side-by-side comparison of two developers' portfolios."""
from __future__ import annotations

from typing import Any

from app.services import portfolio_service

OTHER_LANGUAGE = "Other"

# (key, label) in display order.
METRICS: list[tuple[str, str]] = [
    ("followers", "Followers"),
    ("total_stars", "Total stars"),
    ("total_forks", "Total forks"),
    ("total_repos", "Repositories"),
    ("total_contributions", "Contributions (1y)"),
    ("current_streak", "Current streak"),
    ("longest_streak", "Longest streak"),
]


def _language_names(portfolio: dict[str, Any]) -> list[str]:
    languages = (portfolio.get("stats") or {}).get("top_languages") or []
    return [lang["name"] for lang in languages if lang.get("name") and lang["name"] != OTHER_LANGUAGE]


def developer_summary(portfolio: dict[str, Any]) -> dict[str, Any]:
    """Flatten a portfolio into the contract's `developers[]` item."""
    profile = portfolio.get("profile") or {}
    stats = portfolio.get("stats") or {}
    contrib = portfolio.get("contributions") or {}
    languages = _language_names(portfolio)
    return {
        "login": profile["login"],
        "name": profile.get("name"),
        "avatar_url": profile.get("avatar_url"),
        "html_url": profile.get("html_url"),
        "followers": int(profile.get("followers") or 0),
        "total_stars": int(stats.get("total_stars") or 0),
        "total_forks": int(stats.get("total_forks") or 0),
        "total_repos": int(stats.get("total_repos") or 0),
        "top_language": languages[0] if languages else None,
        "total_contributions": int(contrib.get("total") or 0),
        "current_streak": int(contrib.get("current_streak") or 0),
        "longest_streak": int(contrib.get("longest_streak") or 0),
    }


def _summary(logins: list[str], wins: list[int], total: int) -> str:
    a, b = logins
    wa, wb = wins
    if wa == wb:
        return f"{a} and {b} are evenly matched ({wa}–{wb})."
    leader, leader_wins = (a, wa) if wa > wb else (b, wb)
    noun = "metric" if total == 1 else "metrics"
    return f"{leader} leads in {leader_wins} of {total} {noun}."


def compare_developers(portfolios: list[dict[str, Any]]) -> dict[str, Any]:
    """Compare exactly two portfolios (pure function)."""
    if len(portfolios) != 2:
        raise ValueError("compare_developers requires exactly two portfolios")
    developers = [developer_summary(p) for p in portfolios]
    logins = [d["login"] for d in developers]

    wins = [0, 0]
    metrics = []
    for key, label in METRICS:
        values = [d[key] for d in developers]
        leader: str | None = None
        if values[0] > values[1]:
            leader, wins[0] = logins[0], wins[0] + 1
        elif values[1] > values[0]:
            leader, wins[1] = logins[1], wins[1] + 1
        metrics.append({"key": key, "label": label, "values": values, "leader": leader})

    shared = sorted(set(_language_names(portfolios[0])) & set(_language_names(portfolios[1])))
    return {
        "developers": developers,
        "metrics": metrics,
        "shared_languages": shared,
        "summary": _summary(logins, wins, len(METRICS)),
    }


def compare(usernames: list[str]) -> dict[str, Any]:
    """Fetch both portfolios (cache-aware) and compare them."""
    portfolios = [portfolio_service.get_portfolio(name) for name in usernames]
    return compare_developers(portfolios)
