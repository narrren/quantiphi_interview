"""Shared test setup: isolated temporary SQLite DB and no GitHub token (no real network/DB)."""
from __future__ import annotations

import os
import shutil
import sys
import tempfile
from collections.abc import Iterator
from pathlib import Path

import pytest

_TMP_DIR = Path(tempfile.mkdtemp(prefix="portfolio-tests-"))
os.environ["DB_PATH"] = str(_TMP_DIR / "test.db")
os.environ["GITHUB_TOKEN"] = ""
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.config import settings  # noqa: E402
from app.core.database import init_db  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_db() -> Iterator[None]:
    """Give every test an empty, initialized database."""
    for suffix in ("", "-wal", "-shm"):
        Path(f"{settings.db_path}{suffix}").unlink(missing_ok=True)
    init_db()
    yield


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    shutil.rmtree(_TMP_DIR, ignore_errors=True)
