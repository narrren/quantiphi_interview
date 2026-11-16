"""Domain exceptions, translated to HTTP responses in app.main."""
from __future__ import annotations


class AppError(Exception):
    status_code: int = 500

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class GitHubUserNotFound(AppError):
    status_code = 404


class GitHubRateLimited(AppError):
    status_code = 429


class UpstreamError(AppError):
    status_code = 502
