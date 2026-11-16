# API Contract (source of truth for backend + frontend)

Base URL: `/api` (backend on `http://localhost:8000`, Vite dev server proxies `/api` → 8000).
All errors: HTTP status + JSON `{"detail": "<human readable message>"}`.
All business logic (aggregation, streaks, percentages, matching) is server-side.
The frontend only renders.

## GET /api/health
`{"status": "ok"}`

## GET /api/portfolio/{username}?refresh=false
Returns cached data from SQLite when fresh (TTL from settings `cache_ttl_seconds`, default 3600).
`refresh=true` forces a GitHub refetch. If GitHub fails (rate limit / network) and a stale cache
exists, stale cache is served with `cache.stale = true`.

```json
{
  "profile": {
    "login": "octocat", "name": "The Octocat", "avatar_url": "https://...", "bio": "...",
    "company": "...", "location": "...", "blog": "...", "html_url": "https://github.com/octocat",
    "followers": 10, "following": 2, "public_repos": 8, "created_at": "2011-01-25T18:44:36Z"
  },
  "stats": {
    "total_stars": 120, "total_forks": 40, "total_repos": 8,
    "top_languages": [ {"name": "Python", "count": 4, "percentage": 50.0, "color": "#3572A5"} ]
  },
  "repositories": [
    {
      "id": 1, "name": "hello", "full_name": "octocat/hello", "description": "..." ,
      "html_url": "https://github.com/octocat/hello", "stars": 10, "forks": 2,
      "language": "Python", "language_color": "#3572A5", "topics": ["api"],
      "updated_at": "2024-01-01T00:00:00Z", "is_fork": false
    }
  ],
  "contributions": {
    "total": 1234,
    "weeks": [ [ {"date": "2025-11-16", "count": 5, "level": 1} ] ],
    "current_streak": 3, "longest_streak": 21,
    "best_day": {"date": "2026-03-01", "count": 40},
    "source": "graphql | scrape | unavailable"
  },
  "cache": {"cached": true, "fetched_at": "2026-11-16T22:30:00+00:00", "ttl_seconds": 3600, "stale": false}
}
```
- `top_languages`: by number of non-fork repos with that primary language; top 6, rest merged into
  `"Other"` (color `#8b949e`); percentages rounded to 1 decimal.
- `repositories`: non-fork first, sorted by stars desc then updated_at desc. `description` may be null.
- `weeks`: list of weeks (oldest first), each a list of up to 7 days Sunday→Saturday. `level` 0–4.
- Errors: 404 user not found; 429 rate limited and no cache; 502 GitHub unreachable and no cache;
  422 invalid username (must match `^[A-Za-z0-9](?:[A-Za-z0-9-]{0,38})$`).

## GET /api/settings  → `{"default_username": "octocat", "theme": "dark", "cache_ttl_seconds": 3600, "last_job_description": ""}`
## PUT /api/settings  (partial body, same keys) → full settings object
Validation: theme ∈ {light, dark}; 60 ≤ cache_ttl_seconds ≤ 86400; username regex above; JD ≤ 20000 chars.

## POST /api/match   — "Tech Stack Compatibility" (The Vibe Check)
Request: `{"username": "octocat", "job_description": "We need a Python + React dev..."}`
(job_description 20–20000 chars, else 422). Uses the user's cached repositories (fetches if absent).
Response:
```json
{
  "match_percentage": 67, "grade": "Strong",
  "matched": [ {"keyword": "Python", "category": "language", "evidence": ["repo-a", "repo-b"]} ],
  "missing": [ {"keyword": "Kubernetes", "category": "tool"} ],
  "jd_keywords_count": 3,
  "summary": "2 of 3 technologies in the job description appear in octocat's repositories."
}
```
grade: ≥80 Excellent, ≥60 Strong, ≥40 Moderate, else Low. If JD contains no known tech keyword →
match_percentage 0, grade "Low", summary explains. Last JD saved to settings `last_job_description`.
