from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from app.chatbot import ChatMessage
from app.region import Region
from integrations.history import HistoryStore

_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_sessions (
  user_id TEXT PRIMARY KEY,
  channel TEXT NOT NULL,
  region TEXT,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id, created_at);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class SQLiteHistoryStore(HistoryStore):
    def __init__(self, db_path: Path, max_messages: int = 12) -> None:
        self._db_path = db_path
        self._max_messages = max_messages
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.executescript(_SCHEMA)

    def ensure_session(self, user_id: str, channel: str) -> None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT user_id FROM user_sessions WHERE user_id = ?",
                (user_id,),
            ).fetchone()
            if row is None:
                conn.execute(
                    "INSERT INTO user_sessions (user_id, channel, region, updated_at) "
                    "VALUES (?, ?, NULL, ?)",
                    (user_id, channel, _utc_now()),
                )
            else:
                conn.execute(
                    "UPDATE user_sessions SET updated_at = ? WHERE user_id = ?",
                    (_utc_now(), user_id),
                )

    def get(self, user_id: str) -> list[ChatMessage]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT role, content FROM messages WHERE user_id = ? "
                "ORDER BY created_at ASC, id ASC",
                (user_id,),
            ).fetchall()
        return [ChatMessage(role=row["role"], content=row["content"]) for row in rows]

    def add_turn(self, user_id: str, user_text: str, assistant_text: str) -> None:
        now = _utc_now()
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (user_id, "user", user_text, now),
            )
            conn.execute(
                "INSERT INTO messages (user_id, role, content, created_at) VALUES (?, ?, ?, ?)",
                (user_id, "assistant", assistant_text, now),
            )
            conn.execute(
                "UPDATE user_sessions SET updated_at = ? WHERE user_id = ?",
                (now, user_id),
            )
            excess = conn.execute(
                "SELECT COUNT(*) AS cnt FROM messages WHERE user_id = ?",
                (user_id,),
            ).fetchone()["cnt"] - self._max_messages
            if excess > 0:
                conn.execute(
                    "DELETE FROM messages WHERE id IN ("
                    "  SELECT id FROM messages WHERE user_id = ? "
                    "  ORDER BY created_at ASC, id ASC LIMIT ?"
                    ")",
                    (user_id, excess),
                )

    def clear(self, user_id: str) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM messages WHERE user_id = ?", (user_id,))
            conn.execute(
                "UPDATE user_sessions SET region = NULL, updated_at = ? WHERE user_id = ?",
                (_utc_now(), user_id),
            )

    def get_region(self, user_id: str) -> Region | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT region FROM user_sessions WHERE user_id = ?",
                (user_id,),
            ).fetchone()
        if row is None or row["region"] is None:
            return None
        return row["region"]  # type: ignore[return-value]

    def set_region(self, user_id: str, region: Region) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE user_sessions SET region = ?, updated_at = ? WHERE user_id = ?",
                (region, _utc_now(), user_id),
            )
