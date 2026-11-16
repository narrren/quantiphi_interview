"""Shared app factory for compare/badge endpoint tests.

Uses app.main when it already registers the compare/badge routers; otherwise builds a
minimal app with the same AppError handler so these tests don't depend on wiring order.
"""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.errors import AppError
from app.routers import badge, compare


def build_app() -> FastAPI:
    try:
        from app.main import app as main_app

        main_app.url_path_for("read_compare")
        main_app.url_path_for("read_badge", username="x")
        return main_app
    except Exception:  # pragma: no cover - main app not wired yet
        pass
    app = FastAPI()

    @app.exception_handler(AppError)
    async def app_error_handler(_: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    app.include_router(compare.router, prefix="/api")
    app.include_router(badge.router, prefix="/api")
    return app
