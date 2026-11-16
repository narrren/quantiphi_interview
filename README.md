# DevFolio — GitHub Developer Portfolio

A professional developer dashboard that turns any GitHub profile into a personal-branding page:
contribution heatmap with coding streaks, repository cards, profile stats with a Top Languages
chart, and a **Tech Stack Compatibility** score against any job description — plus an AI-style
**Portfolio Assistant chatbot** and a **Recruiter Pitch Generator**.

## Features

| Area | Feature |
|---|---|
| Frontend | **Contribution Graph** — 53-week heatmap coloured by intensity (levels 0–4), month/weekday labels, tooltips |
| | **Coding streaks** — total contributions, current streak, longest streak, best day |
| | **Repository Cards** — stars, forks, language tag + colour, description, topics; search / filter / sort |
| | **Profile Header** — avatar, bio, followers, following, total stars, forks, repos, **Top Languages donut chart** |
| Backend | **GitHub API integration** — REST v3 for profile + repositories; GraphQL v4 contribution calendar when `GITHUB_TOKEN` is set, public contribution calendar otherwise |
| | **SQLite caching engine** — repository metadata, profile, contributions, user settings and chat history cached locally with a configurable TTL; stale cache is served if GitHub is rate-limited or unreachable |
| Vibe Check | **Tech Stack Compatibility** — paste a job description; the backend extracts tech keywords (≈50-entry taxonomy with aliases, e.g. `golang`, `reactjs`, `c#`) and compares them against the languages/topics of the user's cached repos → **Match Percentage badge** at the top of the profile with matched / missing skills and evidence repos |
| Extra 1 | **Portfolio Assistant (chatbot)** — conversational Q&A over the cached portfolio ("What are the strongest languages?", "Tell me about repo X", "Why should I hire them?", "Do they know Docker?"), intent detection, follow-up suggestion chips, history persisted in SQLite |
| Extra 2 | **Recruiter Pitch Generator** — generates a headline, bio (professional / friendly / concise tone), highlight bullets and actionable **skill-gap tips** for the missing JD skills; one-click copy |

## Architecture

```
quantiphi_interview/
├── backend/                     FastAPI (Python 3.11+)
│   ├── app/
│   │   ├── main.py              App factory, CORS, error handling, router wiring, SPA serving
│   │   ├── core/                config, SQLite connection + schema, domain errors
│   │   ├── repositories/        Data-access layer (SQLite): cache, settings, chat history
│   │   ├── services/            Business logic: GitHub client, contributions + streaks,
│   │   │                        portfolio aggregation/caching, match scoring, chatbot, pitch
│   │   ├── schemas/             Pydantic request/response models + validation
│   │   └── routers/             Thin HTTP layer: portfolio, settings, match, chat, pitch
│   └── tests/                   pytest unit + API tests (no network)
├── frontend/                    React 18 + TypeScript + Vite (presentation only)
│   └── src/{api,components,hooks,types.ts}
└── docs/API_CONTRACT.md         Request/response contract shared by both tiers
```

**Design principles**
- *All business logic is server-side* — aggregation, percentages, streaks, keyword matching, chatbot
  intents and pitch generation live in `backend/app/services`. The frontend only renders.
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
| POST | `/api/chat` | Portfolio Assistant chatbot reply |
| GET / DELETE | `/api/chat/{username}/history` | Chat history |
| POST | `/api/pitch` | Recruiter pitch generation |

Full shapes: [docs/API_CONTRACT.md](docs/API_CONTRACT.md). Interactive docs: `http://localhost:8000/docs`.

## Match Percentage — how it is computed

1. The JD is scanned for known technologies (case-insensitive, whole-token, alias-aware).
2. Each technology is *matched* when a cached repository provides evidence — its primary language
   (e.g. `React` ⇐ JavaScript/TypeScript repos) or its topics / name / description.
3. `match % = Σ weight(matched) / Σ weight(all JD technologies)`, where programming languages weigh 2×
   and frameworks/tools 1×.
4. Grade: ≥80 Excellent · ≥60 Strong · ≥40 Moderate · otherwise Low.
