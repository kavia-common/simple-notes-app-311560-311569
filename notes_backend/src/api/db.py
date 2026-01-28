"""SQLite database utilities for the Notes app.

This module keeps persistence logic isolated from the FastAPI routes:
- Resolves the DB path from env var SQLITE_DB (used by the provided SQLite container)
- Creates tables on startup (simple migration)
- Provides helper functions for CRUD operations.

We intentionally use the Python stdlib `sqlite3` module to avoid extra dependencies.
"""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from typing import Generator, Optional


def _resolve_db_path() -> str:
    """Resolve the SQLite DB file path.

    Uses SQLITE_DB env var if present (expected with the database container),
    otherwise falls back to a local file in the container working directory.
    """
    return os.getenv("SQLITE_DB", "notes.db")


def _dict_factory(cursor: sqlite3.Cursor, row: sqlite3.Row) -> dict:
    """Convert sqlite rows to dicts keyed by column names."""
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


# PUBLIC_INTERFACE
@contextmanager
def get_connection() -> Generator[sqlite3.Connection, None, None]:
    """Get a SQLite connection configured for this app.

    Returns a contextmanager yielding a connection that:
    - Uses Row->dict factory for convenient JSON serialization
    - Has foreign keys enabled
    """
    db_path = _resolve_db_path()
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = _dict_factory
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        yield conn
    finally:
        conn.close()


# PUBLIC_INTERFACE
def init_db() -> None:
    """Initialize/migrate the database schema.

    This is a lightweight migration strategy for a small demo app:
    - Create notes table if not present
    - Add missing columns if schema evolves (via pragma table_info checks)
    """
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
            """
        )

        # Simple "migration": ensure required columns exist (safe no-op if present).
        existing_cols = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(notes);").fetchall()
        }
        required_cols = {
            "id",
            "title",
            "content",
            "created_at",
            "updated_at",
        }

        missing = required_cols - existing_cols
        # If we ever add new columns later, we can handle them here; for now,
        # this mainly validates schema presence.
        if missing:
            # In a real app, we'd add ALTER TABLE statements per missing column.
            # For this simple app, re-creating is not feasible without data loss,
            # so we raise an explicit error.
            raise RuntimeError(
                f"Database schema for 'notes' missing columns: {sorted(missing)}"
            )

        # Trigger WAL for better concurrent read/write behavior.
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.commit()


# PUBLIC_INTERFACE
def now_iso(conn: sqlite3.Connection) -> str:
    """Return database time (ISO-ish string) using SQLite's clock."""
    row = conn.execute("SELECT datetime('now') as now;").fetchone()
    return str(row["now"])


# PUBLIC_INTERFACE
def fetch_note(conn: sqlite3.Connection, note_id: int) -> Optional[dict]:
    """Fetch a note by id; returns None if not found."""
    return conn.execute(
        "SELECT id, title, content, created_at, updated_at FROM notes WHERE id = ?;",
        (note_id,),
    ).fetchone()

