"""SQLite persistence for cached GitHub data (profile, repositories, contribution calendar)."""
from __future__ import annotations

import json
from typing import Any

from app.core.database import get_connection


def save_snapshot(
    username: str,
    profile: dict[str, Any],
    repositories: list[dict[str, Any]],
    days: list[dict[str, Any]],
    source: str,
    fetched_at: float,
) -> None:
    """Atomically replace everything cached for `username` with a fresh snapshot."""
    with get_connection() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO users (username, payload, fetched_at) VALUES (?, ?, ?)",
            (username, json.dumps(profile), fetched_at),
        )
        conn.execute("DELETE FROM repositories WHERE username = ?", (username,))
        conn.executemany(
            """INSERT OR REPLACE INTO repositories
               (id, username, name, full_name, description, html_url, stars, forks,
                language, topics, updated_at, is_fork, fetched_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    r["id"], username, r["name"], r["full_name"], r["description"],
                    r["html_url"], r["stars"], r["forks"], r["language"],
                    json.dumps(r["topics"]), r["updated_at"], int(r["is_fork"]), fetched_at,
                )
                for r in repositories
            ],
        )
        conn.execute("DELETE FROM contributions WHERE username = ?", (username,))
        conn.executemany(
            "INSERT INTO contributions (username, date, count, level) VALUES (?, ?, ?, ?)",
            [(username, d["date"], d["count"], d["level"]) for d in days],
        )
        conn.execute(
            """INSERT OR REPLACE INTO contribution_meta (username, source, total, fetched_at)
               VALUES (?, ?, ?, ?)""",
            (username, source, sum(d["count"] for d in days), fetched_at),
        )


def load_snapshot(username: str) -> dict[str, Any] | None:
    """Return the cached snapshot for `username` (case-insensitive) or None if absent.

    Shape: {"profile", "repositories", "days", "source", "fetched_at"}.
    """
    with get_connection() as conn:
        user = conn.execute(
            "SELECT payload, fetched_at FROM users WHERE username = ?", (username,)
        ).fetchone()
        if user is None:
            return None
        repo_rows = conn.execute(
            "SELECT * FROM repositories WHERE username = ?", (username,)
        ).fetchall()
        day_rows = conn.execute(
            "SELECT date, count, level FROM contributions WHERE username = ? ORDER BY date",
            (username,),
        ).fetchall()
        meta = conn.execute(
            "SELECT source FROM contribution_meta WHERE username = ?", (username,)
        ).fetchone()

    repositories = [
        {
            "id": row["id"],
            "name": row["name"],
            "full_name": row["full_name"],
            "description": row["description"],
            "html_url": row["html_url"],
            "stars": row["stars"],
            "forks": row["forks"],
            "language": row["language"],
            "topics": json.loads(row["topics"]),
            "updated_at": row["updated_at"],
            "is_fork": bool(row["is_fork"]),
        }
        for row in repo_rows
    ]
    return {
        "profile": json.loads(user["payload"]),
        "repositories": repositories,
        "days": [dict(row) for row in day_rows],
        "source": meta["source"] if meta else "unavailable",
        "fetched_at": user["fetched_at"],
    }
