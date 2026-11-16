"""FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.database import init_db
from app.core.errors import AppError
from app.routers import badge, compare, insights, match, portfolio, user_settings


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="GitHub Developer Portfolio API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


app.include_router(portfolio.router, prefix="/api")
app.include_router(user_settings.router, prefix="/api")
app.include_router(match.router, prefix="/api")
app.include_router(insights.router, prefix="/api")
app.include_router(compare.router, prefix="/api")
app.include_router(badge.router, prefix="/api")

# Serve the production frontend build (single-process deployment) when present.
if settings.frontend_dist.is_dir():
    app.mount("/assets", StaticFiles(directory=settings.frontend_dist / "assets"), name="assets")

    dist_root = settings.frontend_dist.resolve()

    @app.get("/{full_path:path}", include_in_schema=False)
    def spa(full_path: str) -> FileResponse:
        # Unknown API routes must stay JSON 404s, not fall through to the SPA.
        if full_path == "api" or full_path.startswith("api/"):
            raise AppError("Not Found", status_code=404)
        # Serve real top-level build files (e.g. favicon.svg) without escaping dist/.
        candidate = (dist_root / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(dist_root):
            return FileResponse(candidate)
        return FileResponse(dist_root / "index.html")
