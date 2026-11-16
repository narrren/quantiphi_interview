"""SQLite persistence for user settings (key/value with JSON-encoded values)."""
from __future__ import annotations

import json
from typing import Any

from app.core.database import get_connection


def get_all() -> dict[str, Any]:
    """Return every stored setting as a decoded dict."""
    with get_connection() as conn:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
    return {row["key"]: json.loads(row["value"]) for row in rows}


def set_many(values: dict[str, Any]) -> None:
    """Upsert the given settings in a single transaction."""
    with get_connection() as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            [(key, json.dumps(value)) for key, value in values.items()],
        )
