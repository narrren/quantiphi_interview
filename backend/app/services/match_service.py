"""Tech Stack Compatibility ("The Vibe Check"): compare a job description against a portfolio."""
from __future__ import annotations

from typing import Any

from app.services.tech_keywords import Tech, extract_technologies

LANGUAGE_WEIGHT = 2
OTHER_WEIGHT = 1
MAX_EVIDENCE = 5


def grade_for(percentage: int) -> str:
    """Map a match percentage to its contract grade."""
    if percentage >= 80:
        return "Excellent"
    if percentage >= 60:
        return "Strong"
    if percentage >= 40:
        return "Moderate"
    return "Low"


def repo_mentions(tech: Tech, repo: dict[str, Any]) -> bool:
    """True if ``repo`` evidences ``tech``.

    Evidence is the repo's primary language being one of ``tech.languages`` or a topic naming it.
    Non-language technologies may also be evidenced by the repo name or description.
    """
    if repo.get("language") in tech.languages:
        return True
    if any(tech.in_identifier(topic) for topic in repo.get("topics") or []):
        return True
    if tech.category == "language":
        return False
    return tech.in_identifier(repo.get("name") or "") or tech.in_text(repo.get("description") or "")


def evidence_for(tech: Tech, repositories: list[dict[str, Any]]) -> list[str]:
    """Names of original (non-fork) repos evidencing ``tech``, most starred first, capped."""
    hits = [r for r in repositories if not r.get("is_fork") and repo_mentions(tech, r)]
    hits.sort(key=lambda r: r.get("stars") or 0, reverse=True)
    return [r["name"] for r in hits[:MAX_EVIDENCE]]


def compute_match(portfolio: dict[str, Any], job_description: str) -> dict[str, Any]:
    """Score how well a portfolio covers the technologies named in ``job_description``.

    Each distinct known technology in the JD is a keyword. Language keywords weigh
    ``LANGUAGE_WEIGHT`` (2) and every other category ``OTHER_WEIGHT`` (1), so
    ``match_percentage = round(100 * matched_weight / total_weight)``. Only original repositories
    count as evidence, since forks do not demonstrate the user's own work.
    """
    username = portfolio["profile"]["login"]
    repositories = portfolio.get("repositories") or []
    keywords = extract_technologies(job_description)
    if not keywords:
        return {
            "match_percentage": 0,
            "grade": "Low",
            "matched": [],
            "missing": [],
            "jd_keywords_count": 0,
            "summary": "No recognizable technologies were found in the job description, "
            "so a compatibility score could not be computed.",
        }

    matched: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    matched_weight = total_weight = 0
    for tech in keywords:
        weight = LANGUAGE_WEIGHT if tech.category == "language" else OTHER_WEIGHT
        total_weight += weight
        evidence = evidence_for(tech, repositories)
        if evidence:
            matched_weight += weight
            matched.append({"keyword": tech.name, "category": tech.category, "evidence": evidence})
        else:
            missing.append({"keyword": tech.name, "category": tech.category})

    percentage = round(100 * matched_weight / total_weight)
    noun = "technology" if len(keywords) == 1 else "technologies"
    return {
        "match_percentage": percentage,
        "grade": grade_for(percentage),
        "matched": matched,
        "missing": missing,
        "jd_keywords_count": len(keywords),
        "summary": f"{len(matched)} of {len(keywords)} {noun} in the job description appear in "
        f"{username}'s repositories.",
    }
