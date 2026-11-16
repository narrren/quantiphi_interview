"""Compare Developers endpoint."""
from __future__ import annotations

import re
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from app.core.config import USERNAME_PATTERN
from app.schemas.compare import CompareOut
from app.services import compare_service

router = APIRouter(tags=["compare"])

_USERNAME_RE = re.compile(USERNAME_PATTERN)


def parse_users(raw: str) -> list[str]:
    """Validate `users=alice,bob`: exactly two distinct (case-insensitive) valid usernames."""
    names = [part.strip() for part in raw.split(",")]
    if len(names) != 2 or not all(names):
        raise HTTPException(
            status_code=422,
            detail="Provide exactly two comma-separated GitHub usernames, e.g. users=alice,bob.",
        )
    invalid = [n for n in names if not _USERNAME_RE.fullmatch(n)]
    if invalid:
        raise HTTPException(
            status_code=422, detail=f"Invalid GitHub username: {invalid[0]!r}."
        )
    if names[0].lower() == names[1].lower():
        raise HTTPException(status_code=422, detail="Provide two different GitHub usernames.")
    return names


@router.get("/compare", response_model=CompareOut)
def read_compare(users: Annotated[str, Query(max_length=100)]) -> dict[str, Any]:
    """Compare two developers side by side."""
    return compare_service.compare(parse_users(users))
