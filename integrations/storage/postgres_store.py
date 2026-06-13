from __future__ import annotations

from datetime import datetime, timezone

import psycopg2
import psycopg2.extras

from app.chatbot import ChatMessage
from app.config import normalize_database_url
from app.region import Region
from integrations.history import HistoryStore

_SCHEMA = """
CREATE TABLE IF NOT EXISTS user_sessions (
  user_id TEXT PRIMARY KEY,
  channel TEXT NOT NULL,
  region TEXT,
  updated_at TIMESTAMPTZ NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
  id SERIAL PRIMARY KEY,
  user_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_messages_user ON messages(user_id, created_at);
"""


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class PostgresHistoryStore(HistoryStore):
    """Postgres-backed store — works with Supabase and any Postgres provider."""

    def __init__(self, database_url: str, max_messages: int = 12) -> None:
        self._database_url = normalize_database_url(database_url)
        self._max_messages = max_messages
        self._init_schema()

    def _connect(self):
        return psycopg2.connect(self._database_url)

    def _init_schema(self) -> None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(_SCHEMA)
            conn.commit()

    def ensure_session(self, user_id: str, channel: str) -> None:
        now = _utc_now()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT user_id FROM user_sessions WHERE user_id = %s",
                    (user_id,),
                )
                if cur.fetchone() is None:
                    cur.execute(
                        "INSERT INTO user_sessions (user_id, channel, region, updated_at) "
                        "VALUES (%s, %s, NULL, %s)",
                        (user_id, channel, now),
                    )
                else:
                    cur.execute(
                        "UPDATE user_sessions SET updated_at = %s WHERE user_id = %s",
                        (now, user_id),
                    )
            conn.commit()

    def get(self, user_id: str) -> list[ChatMessage]:
        with self._connect() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
                cur.execute(
                    "SELECT role, content FROM messages WHERE user_id = %s "
                    "ORDER BY created_at ASC, id ASC",
                    (user_id,),
                )
                rows = cur.fetchall()
        return [ChatMessage(role=row["role"], content=row["content"]) for row in rows]

    def add_turn(self, user_id: str, user_text: str, assistant_text: str) -> None:
        now = _utc_now()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO messages (user_id, role, content, created_at) "
                    "VALUES (%s, %s, %s, %s)",
                    (user_id, "user", user_text, now),
                )
                cur.execute(
                    "INSERT INTO messages (user_id, role, content, created_at) "
                    "VALUES (%s, %s, %s, %s)",
                    (user_id, "assistant", assistant_text, now),
                )
                cur.execute(
                    "UPDATE user_sessions SET updated_at = %s WHERE user_id = %s",
                    (now, user_id),
                )
                cur.execute(
                    "SELECT COUNT(*) FROM messages WHERE user_id = %s",
                    (user_id,),
                )
                count = cur.fetchone()[0]
                excess = count - self._max_messages
                if excess > 0:
                    cur.execute(
                        "DELETE FROM messages WHERE id IN ("
                        "  SELECT id FROM messages WHERE user_id = %s "
                        "  ORDER BY created_at ASC, id ASC LIMIT %s"
                        ")",
                        (user_id, excess),
                    )
            conn.commit()

    def clear(self, user_id: str) -> None:
        now = _utc_now()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM messages WHERE user_id = %s", (user_id,))
                cur.execute(
                    "UPDATE user_sessions SET region = NULL, updated_at = %s "
                    "WHERE user_id = %s",
                    (now, user_id),
                )
            conn.commit()

    def get_region(self, user_id: str) -> Region | None:
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT region FROM user_sessions WHERE user_id = %s",
                    (user_id,),
                )
                row = cur.fetchone()
        if row is None or row[0] is None:
            return None
        return row[0]  # type: ignore[return-value]

    def set_region(self, user_id: str, region: Region) -> None:
        now = _utc_now()
        with self._connect() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE user_sessions SET region = %s, updated_at = %s "
                    "WHERE user_id = %s",
                    (region, now, user_id),
                )
            conn.commit()
