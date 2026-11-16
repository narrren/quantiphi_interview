# DevFolio — GitHub Developer Portfolio

A professional developer dashboard that turns any GitHub profile into a personal-branding page:
contribution heatmap with coding streaks, repository cards, profile stats with a Top Languages
chart, and a **Tech Stack Compatibility** score against any job description.

## Features

| Area | Feature |
|---|---|
| Frontend | **Contribution Graph** — 53-week heatmap coloured by intensity (levels 0–4), month/weekday labels, tooltips |
| | **Coding streaks** — total contributions, current streak, longest streak, best day |
| | **Repository Cards** — stars, forks, language tag + colour, description, topics; search / filter / sort |
| | **Profile Header** — avatar, bio, followers, following, total stars, forks, repos, **Top Languages donut chart** |
| Backend | **GitHub API integration** — REST v3 for profile + repositories; GraphQL v4 contribution calendar when `GITHUB_TOKEN` is set, public contribution calendar otherwise |
| | **SQLite caching engine** — repository metadata, profile, contributions and user settings cached locally with a configurable TTL; stale cache is served if GitHub is rate-limited or unreachable |
| Vibe Check | **Tech Stack Compatibility** — paste a job description; the backend extracts tech keywords (60+ technology taxonomy with aliases, e.g. `golang`, `reactjs`, `c#`) and compares them against the languages/topics of the user's cached repos → **Match Percentage badge** at the top of the profile with matched / missing skills and evidence repos |

### Advanced features (behind the "Explore advanced features" button)

| Feature | Why it matters |
|---|---|
| **Developer Insights** | Weekday coding rhythm, 12-month contribution trend, consistency %, average per active day and a 30-day momentum indicator — recruiters see *how* someone codes, not just how much |
| **Portfolio Readiness Score** | 0–100 score with a checklist (bio, website, descriptions, topics, licenses, recent activity, popular project, consistency), per-repo health scores and concrete "how to improve" actions — turns the dashboard into a personal-branding coach |
| **Compare Developers** | Head-to-head view of two GitHub users across 7 metrics with leaders, shared languages and a summary — useful for hiring shortlists |
| **Share & Embed badges** | Live SVG badges (`/api/badge/{user}?metric=stars`) for stars, followers, contributions, streak and top language, embeddable in any README, plus deep links (`?user=`, `?compare=a,b`) |

## Architecture

```
quantiphi_interview/
├── backend/                     FastAPI (Python 3.11+)
│   ├── app/
│   │   ├── main.py              App factory, CORS, error handling, router wiring, SPA serving
│   │   ├── core/                config, SQLite connection + schema, domain errors
│   │   ├── repositories/        Data-access layer (SQLite): cache, settings
│   │   ├── services/            Business logic: GitHub client, contributions + streaks,
│   │   │                        portfolio aggregation/caching, match scoring,
│   │   │                        insights + readiness, comparison, badge rendering
│   │   ├── schemas/             Pydantic request/response models + validation
│   │   └── routers/             Thin HTTP layer: portfolio, settings, match, insights, compare, badge
│   └── tests/                   pytest unit + API tests (no network)
├── frontend/                    React 18 + TypeScript + Vite (presentation only)
│   └── src/{api,components,hooks,types.ts}
└── docs/API_CONTRACT.md         Request/response contract shared by both tiers
```

**Design principles**
- *All business logic is server-side* — aggregation, percentages, streaks and keyword matching
  live in `backend/app/services`. The frontend only renders.
- *Layered backend* — routers → services → repositories → SQLite; services are pure functions where
  possible, which makes them easy to unit-test.
- *Rate-limit resilience* — cache-first reads with TTL, forced refresh, and stale-cache fallback.

## Getting started

**Prerequisites:** Python 3.11+, Node 18+.

```bash
# 1. Backend  (http://localhost:8000, docs at /docs)
cd backend
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # optional: add GITHUB_TOKEN for 5000 req/h + GraphQL
export $(grep -v '^#' .env | xargs) 2>/dev/null
uvicorn app.main:app --reload --port 8000

# 2. Frontend (http://localhost:5173, proxies /api → :8000)
cd ../frontend
npm install
npm run dev
```

Single-process mode: `cd frontend && npm run build`, then the backend serves the built SPA at
http://localhost:8000.

**Tests:** `cd backend && python3 -m pytest -q`

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/portfolio/{username}?refresh=false` | Profile, stats, top languages, repos, contributions + streaks (cached) |
| GET / PUT | `/api/settings` | User settings (default username, theme, cache TTL, last JD) |
| POST | `/api/match` | Tech Stack Compatibility score for a job description |
| GET | `/api/insights/{username}` | Developer Insights + Portfolio Readiness score |
| GET | `/api/compare?users=a,b` | Compare two developers |
| GET | `/api/badge/{username}?metric=stars` | Embeddable SVG badge |

Full shapes: [docs/API_CONTRACT.md](docs/API_CONTRACT.md). Interactive docs: `http://localhost:8000/docs`.

## Match Percentage — how it is computed

1. The JD is scanned for known technologies (case-insensitive, whole-token, alias-aware).
2. Each technology is *matched* when a cached repository provides evidence — its primary language
   (e.g. `React` ⇐ JavaScript/TypeScript repos) or its topics / name / description.
3. `match % = Σ weight(matched) / Σ weight(all JD technologies)`, where programming languages weigh 2×
   and frameworks/tools 1×.
4. Grade: ≥80 Excellent · ≥60 Strong · ≥40 Moderate · otherwise Low.
