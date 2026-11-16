"""Developer insights (activity patterns) and portfolio readiness scoring (pure functions)."""
from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from typing import Any

from app.services import portfolio_service
from app.services.match_service import grade_for

WEEKDAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
MONTHS = 12
TREND_WINDOW_DAYS = 30
RECENT_ACTIVITY_DAYS = 90
REPO_FRESH_DAYS = 180
POPULAR_STARS = 5
CONSISTENCY_TARGET = 20.0
DESCRIPTION_TARGET = 0.7
TOPICS_TARGET = 0.5
LICENSE_TARGET = 0.5
TOP_REPOS = 6
EXAMPLE_REPOS = 3


def _weekday_index(day: date) -> int:
    """0 = Sunday ... 6 = Saturday."""
    return (day.weekday() + 1) % 7


def _shift_month(year: int, month: int, delta: int) -> tuple[int, int]:
    index = year * 12 + (month - 1) + delta
    return index // 12, index % 12 + 1


def compute_activity(contributions_days: list[dict[str, Any]], today: date) -> dict[str, Any]:
    """Weekday totals, last-12-month buckets, consistency and a 30-day trend."""
    counts: dict[date, int] = {}
    for day in contributions_days:
        current = date.fromisoformat(day["date"])
        counts[current] = counts.get(current, 0) + int(day.get("count") or 0)

    weekday_totals = [0] * 7
    weekday_days = [0] * 7
    for current, count in counts.items():
        index = _weekday_index(current)
        weekday_totals[index] += count
        weekday_days[index] += 1

    month_keys = [_shift_month(today.year, today.month, -offset) for offset in range(MONTHS - 1, -1, -1)]
    month_totals = {key: 0 for key in month_keys}
    for current, count in counts.items():
        key = (current.year, current.month)
        if key in month_totals:
            month_totals[key] += count

    total_days = len(counts)
    active_days = sum(1 for count in counts.values() if count > 0)
    total_count = sum(counts.values())
    best_total = max(weekday_totals)

    last_start = today - timedelta(days=TREND_WINDOW_DAYS - 1)
    previous_start = last_start - timedelta(days=TREND_WINDOW_DAYS)
    last = sum(c for d, c in counts.items() if last_start <= d <= today)
    previous = sum(c for d, c in counts.items() if previous_start <= d < last_start)
    direction = "up" if last > previous else "down" if last < previous else "flat"

    return {
        "weekday_totals": [
            {
                "day": name,
                "total": weekday_totals[i],
                "average": round(weekday_totals[i] / weekday_days[i], 1) if weekday_days[i] else 0.0,
            }
            for i, name in enumerate(WEEKDAYS)
        ],
        "monthly": [
            {
                "month": f"{year:04d}-{month:02d}",
                "label": date(year, month, 1).strftime("%b %Y"),
                "total": month_totals[(year, month)],
            }
            for year, month in month_keys
        ],
        "active_days": active_days,
        "total_days": total_days,
        "consistency_percentage": round(active_days * 100 / total_days, 1) if total_days else 0.0,
        "average_per_active_day": round(total_count / active_days, 1) if active_days else 0.0,
        "most_active_weekday": WEEKDAYS[weekday_totals.index(best_total)] if best_total > 0 else None,
        "trend": {
            "last_30_days": last,
            "previous_30_days": previous,
            "change_percentage": round((last - previous) * 100 / previous, 1) if previous else None,
            "direction": direction,
        },
    }


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _updated_within(repo: dict[str, Any], today: date, days: int) -> bool:
    updated = _parse_date(repo.get("updated_at"))
    return updated is not None and (today - updated).days <= days


def _examples(repos: list[dict[str, Any]]) -> str:
    return ", ".join(r["name"] for r in repos[:EXAMPLE_REPOS])


def _plural(count: int, word: str, plural: str | None = None) -> str:
    return f"{count} {word if count == 1 else (plural or word + 's')}"


def _repos(count: int, adjective: str = "") -> str:
    prefix = f"{adjective} " if adjective else ""
    return _plural(count, f"{prefix}repository", f"{prefix}repositories")


def _coverage_check(
    check_id: str,
    label: str,
    owned: list[dict[str, Any]],
    has: Callable[[dict[str, Any]], bool],
    target: float,
    noun: str,
    action: str,
) -> tuple[dict[str, Any], str | None]:
    """Check that at least `target` of the owned repos satisfy `has`; returns (check, recommendation)."""
    if not owned:
        check = {"id": check_id, "label": label, "passed": False,
                 "detail": "No original (non-fork) repositories to evaluate."}
        return check, "Publish at least one original repository to showcase your work."
    covered = sum(1 for r in owned if has(r))
    ratio = covered / len(owned)
    passed = ratio >= target
    detail = (
        f"{covered} of {len(owned)} original repositories have {noun} "
        f"({round(ratio * 100)}%, target {round(target * 100)}%)."
    )
    recommendation = None
    if not passed:
        missing = [r for r in owned if not has(r)]
        recommendation = (
            f"{action} {_repos(len(missing))} (e.g. {_examples(missing)})."
        )
    return {"id": check_id, "label": label, "passed": passed, "detail": detail}, recommendation


# Weights sum to 100.
WEIGHTS: dict[str, int] = {
    "profile_name": 5,
    "profile_bio": 10,
    "profile_location_or_company": 5,
    "profile_website": 5,
    "repo_descriptions": 15,
    "repo_topics": 10,
    "repo_licenses": 10,
    "recent_activity": 15,
    "popular_project": 10,
    "consistency": 15,
}


def _repo_scores(owned: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    top = sorted(owned, key=lambda r: -int(r.get("stars") or 0))[:TOP_REPOS]
    results = []
    for repo in top:
        criteria = [
            (bool(repo.get("description")), "No description"),
            (bool(repo.get("topics")), "No topics"),
            (bool(repo.get("license")), "No license"),
            (bool(repo.get("homepage")), "No homepage"),
            (_updated_within(repo, today, REPO_FRESH_DAYS), f"Not updated in the last {REPO_FRESH_DAYS} days"),
            (not repo.get("archived"), "Archived"),
        ]
        passed = sum(1 for ok, _ in criteria if ok)
        results.append({
            "name": repo["name"],
            "score": round(passed / len(criteria) * 100),
            "issues": [issue for ok, issue in criteria if not ok],
        })
    return results


def compute_readiness(
    portfolio: dict[str, Any], activity: dict[str, Any], today: date | None = None
) -> dict[str, Any]:
    """Score how recruiter-ready a portfolio is, with checks, recommendations and per-repo scores."""
    today = today or datetime.now(UTC).date()
    profile = portfolio.get("profile") or {}
    repositories = portfolio.get("repositories") or []
    owned = [r for r in repositories if not r.get("is_fork")]

    checks: list[dict[str, Any]] = []
    recommendations: list[str] = []

    def add(check: dict[str, Any], recommendation: str | None) -> None:
        checks.append(check)
        if not check["passed"] and recommendation:
            recommendations.append(recommendation)

    name = profile.get("name")
    add({"id": "profile_name", "label": "Profile has a display name", "passed": bool(name),
         "detail": f"Display name is set to \"{name}\"." if name else "No display name is set."},
        "Set a display name on your GitHub profile so recruiters know who you are.")

    bio = profile.get("bio")
    add({"id": "profile_bio", "label": "Profile has a bio", "passed": bool(bio),
         "detail": f"Bio is set ({len(bio)} characters)." if bio else "No bio is set."},
        "Add a short bio describing your focus areas and core technologies.")

    place = [v for v in (profile.get("location"), profile.get("company")) if v]
    add({"id": "profile_location_or_company", "label": "Profile lists a location or company",
         "passed": bool(place),
         "detail": f"Profile lists: {', '.join(place)}." if place else "Neither location nor company is set."},
        "Add your location or current company to your profile.")

    blog = profile.get("blog")
    add({"id": "profile_website", "label": "Profile links a website", "passed": bool(blog),
         "detail": f"Website: {blog}." if blog else "No website or blog link is set."},
        "Link a personal website, blog or LinkedIn profile from your GitHub profile.")

    add(*_coverage_check("repo_descriptions", "Repositories have descriptions", owned,
                         lambda r: bool(r.get("description")), DESCRIPTION_TARGET,
                         "a description", "Add a one-line description to"))
    add(*_coverage_check("repo_topics", "Repositories have topics", owned,
                         lambda r: bool(r.get("topics")), TOPICS_TARGET,
                         "topics", "Add topics (e.g. language, framework, domain) to"))
    add(*_coverage_check("repo_licenses", "Repositories have a license", owned,
                         lambda r: bool(r.get("license")), LICENSE_TARGET,
                         "a license", "Add a license (e.g. MIT or Apache-2.0) to"))

    recent = [r for r in owned if _updated_within(r, today, RECENT_ACTIVITY_DAYS)]
    latest = max((d for d in (_parse_date(r.get("updated_at")) for r in owned) if d), default=None)
    if recent:
        recent_detail = f"{_repos(len(recent), 'original')} updated in the last {RECENT_ACTIVITY_DAYS} days."
    elif latest:
        recent_detail = f"Most recent update was {(today - latest).days} days ago ({latest.isoformat()})."
    else:
        recent_detail = "No original repositories with update information."
    stale_top = sorted(owned, key=lambda r: -int(r.get("stars") or 0))
    add({"id": "recent_activity", "label": f"Repository updated in the last {RECENT_ACTIVITY_DAYS} days",
         "passed": bool(recent), "detail": recent_detail},
        (f"Push a recent update to one of your key projects (e.g. {_examples(stale_top)}) to show active work."
         if stale_top else "Create and push a new original project to show recent activity."))

    best = max(owned, key=lambda r: int(r.get("stars") or 0), default=None)
    best_stars = int(best.get("stars") or 0) if best else 0
    popular = best_stars >= POPULAR_STARS
    add({"id": "popular_project", "label": f"A project has at least {POPULAR_STARS} stars",
         "passed": popular,
         "detail": (f"Most starred repository is {best['name']} with {_plural(best_stars, 'star')}."
                    if best else "No repositories yet.")},
        (f"Promote your best project (e.g. {best['name']}) with a clear README, demo and screenshots "
         f"to reach {POPULAR_STARS}+ stars." if best else
         "Publish a polished project with a clear README to attract stars."))

    consistency = float(activity.get("consistency_percentage") or 0.0)
    add({"id": "consistency", "label": f"Active on at least {round(CONSISTENCY_TARGET)}% of days",
         "passed": consistency >= CONSISTENCY_TARGET,
         "detail": (f"Active on {activity.get('active_days', 0)} of {activity.get('total_days', 0)} days "
                    f"({consistency}%).")},
        f"Contribute more regularly: you were active on {consistency}% of days; aim for at least "
        f"{round(CONSISTENCY_TARGET)}% (about {round(CONSISTENCY_TARGET * 7 / 100 + 0.5)} days a week).")

    total_weight = sum(WEIGHTS.values())
    earned = sum(WEIGHTS[c["id"]] for c in checks if c["passed"])
    score = round(earned * 100 / total_weight)
    return {
        "score": score,
        "grade": grade_for(score),
        "checks": checks,
        "recommendations": recommendations,
        "repositories": _repo_scores(owned, today),
    }


def get_insights(username: str, refresh: bool = False) -> dict[str, Any]:
    """Build activity insights and portfolio readiness for `username`."""
    portfolio = portfolio_service.get_portfolio(username, refresh=refresh)
    days = [day for week in portfolio["contributions"]["weeks"] for day in week]
    today = datetime.now(UTC).date()
    activity = compute_activity(days, today)
    return {"activity": activity, "readiness": compute_readiness(portfolio, activity, today)}
