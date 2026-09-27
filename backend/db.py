"""SQLite access for the Campus Customs backend."""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
DB_PATH = DATA_DIR / "campus_customs.db"


@contextmanager
def connect(readonly: bool = False) -> Iterator[sqlite3.Connection]:
    """Open the database, commit on success, roll back on error, always close.

    Catalogue reads use readonly=True so they can never write.
    """
    mode = "ro" if readonly else "rw"
    conn = sqlite3.connect(f"file:{DB_PATH}?mode={mode}", uri=True)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_schema() -> None:
    """Create tables the seed database doesn't have yet. Safe to run on every start."""
    with connect() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                token_hash TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                expires_at TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(id)
            );
            CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions(user_id);
            -- Customer memory: each shopper's history is read by user_id, newest first.
            CREATE INDEX IF NOT EXISTS idx_chat_messages_user ON chat_messages(user_id, id);
            """
        )
