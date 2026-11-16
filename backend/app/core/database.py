"""SQLite connection management and schema (the caching engine's storage layer)."""
from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager

from app.core.config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    username    TEXT PRIMARY KEY COLLATE NOCASE,
    payload     TEXT NOT NULL,          -- JSON of the normalized profile
    fetched_at  REAL NOT NULL           -- unix epoch seconds
);

CREATE TABLE IF NOT EXISTS repositories (
    id          INTEGER PRIMARY KEY,
    username    TEXT NOT NULL COLLATE NOCASE,
    name        TEXT NOT NULL,
    full_name   TEXT NOT NULL,
    description TEXT,
    html_url    TEXT NOT NULL,
    stars       INTEGER NOT NULL DEFAULT 0,
    forks       INTEGER NOT NULL DEFAULT 0,
    language    TEXT,
    topics      TEXT NOT NULL DEFAULT '[]',   -- JSON array
    updated_at  TEXT,
    is_fork     INTEGER NOT NULL DEFAULT 0,
    fetched_at  REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_repositories_username ON repositories(username);

CREATE TABLE IF NOT EXISTS contributions (
    username    TEXT NOT NULL COLLATE NOCASE,
    date        TEXT NOT NULL,
    count       INTEGER NOT NULL,
    level       INTEGER NOT NULL,
    PRIMARY KEY (username, date)
);

CREATE TABLE IF NOT EXISTS contribution_meta (
    username    TEXT PRIMARY KEY COLLATE NOCASE,
    source      TEXT NOT NULL,
    total       INTEGER NOT NULL,
    fetched_at  REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key         TEXT PRIMARY KEY,
    value       TEXT NOT NULL               -- JSON encoded value
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    TEXT NOT NULL COLLATE NOCASE,
    role        TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content     TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_chat_username ON chat_messages(username);
"""


def init_db() -> None:
    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.executescript(SCHEMA)


@contextmanager
def get_connection() -> Iterator[sqlite3.Connection]:
    """Yield a connection that commits on success and rolls back on error."""
    conn = sqlite3.connect(settings.db_path, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
