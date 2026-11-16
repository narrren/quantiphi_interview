"""Thin synchronous HTTP client for the GitHub REST/GraphQL APIs and the public contributions page.

Every network or HTTP failure is translated into a domain error from app.core.errors.
"""
from __future__ import annotations

import ssl
from functools import lru_cache
from typing import Any

import httpx

from app.core.config import settings
from app.core.errors import GitHubRateLimited, GitHubUserNotFound, UpstreamError

USER_AGENT = "github-portfolio-app"
CONTRIBUTIONS_PAGE_URL = "https://github.com/users/{username}/contributions"
REPOS_PER_PAGE = 100
MAX_REPO_PAGES = 3

CONTRIBUTIONS_QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { date contributionCount contributionLevel } }
      }
    }
  }
}
"""


def _api_headers() -> dict[str, str]:
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": USER_AGENT,
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if settings.github_token:
        headers["Authorization"] = f"Bearer {settings.github_token}"
    return headers


@lru_cache(maxsize=1)
def _ssl_context() -> ssl.SSLContext | bool:
    """Prefer the OS trust store (works behind TLS-intercepting corporate proxies) when available."""
    try:
        import truststore
    except ImportError:
        return True
    return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)


def _is_rate_limited(response: httpx.Response) -> bool:
    if response.status_code not in (403, 429):
        return False
    if response.headers.get("x-ratelimit-remaining") == "0":
        return True
    return "rate limit" in response.text.lower()


def _request(method: str, url: str, *, headers: dict[str, str], **kwargs: Any) -> httpx.Response:
    """Perform a request and map failures to domain errors (404 -> GitHubUserNotFound)."""
    try:
        with httpx.Client(
            timeout=settings.http_timeout, follow_redirects=True, verify=_ssl_context()
        ) as client:
            response = client.request(method, url, headers=headers, **kwargs)
    except httpx.HTTPError as exc:
        raise UpstreamError(f"Could not reach GitHub: {exc.__class__.__name__}") from exc

    if response.status_code == 404:
        raise GitHubUserNotFound("GitHub user not found")
    if _is_rate_limited(response):
        raise GitHubRateLimited(
            "GitHub API rate limit exceeded. Try again later or configure GITHUB_TOKEN."
        )
    if response.status_code >= 400:
        raise UpstreamError(f"GitHub responded with HTTP {response.status_code}")
    return response


def _json(response: httpx.Response) -> Any:
    try:
        return response.json()
    except ValueError as exc:
        raise UpstreamError("GitHub returned an invalid JSON response") from exc


def fetch_user(username: str) -> dict[str, Any]:
    """Return the raw GitHub user object."""
    url = f"{settings.github_api_url}/users/{username}"
    return _json(_request("GET", url, headers=_api_headers()))


def fetch_repositories(username: str) -> list[dict[str, Any]]:
    """Return the raw owned repositories of a user (up to MAX_REPO_PAGES pages)."""
    url = f"{settings.github_api_url}/users/{username}/repos"
    repos: list[dict[str, Any]] = []
    for page in range(1, MAX_REPO_PAGES + 1):
        params = {"per_page": REPOS_PER_PAGE, "sort": "updated", "type": "owner", "page": page}
        batch = _json(_request("GET", url, headers=_api_headers(), params=params))
        if not isinstance(batch, list):
            raise UpstreamError("Unexpected repository payload from GitHub")
        repos.extend(batch)
        if len(batch) < REPOS_PER_PAGE:
            break
    return repos


def fetch_contribution_calendar(username: str) -> dict[str, Any]:
    """Return the GraphQL contributionCalendar object (requires a token)."""
    if not settings.github_token:
        raise UpstreamError("GraphQL API requires GITHUB_TOKEN")
    payload = _json(
        _request(
            "POST",
            f"{settings.github_api_url}/graphql",
            headers=_api_headers(),
            json={"query": CONTRIBUTIONS_QUERY, "variables": {"login": username}},
        )
    )
    user = (payload.get("data") or {}).get("user") if isinstance(payload, dict) else None
    if not user:
        raise UpstreamError("GraphQL contribution query returned no data")
    return user["contributionsCollection"]["contributionCalendar"]


def fetch_contributions_html(username: str) -> str:
    """Return the HTML fragment of the public contribution calendar (no auth)."""
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html"}
    return _request("GET", CONTRIBUTIONS_PAGE_URL.format(username=username), headers=headers).text
