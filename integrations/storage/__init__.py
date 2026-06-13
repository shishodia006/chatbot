from __future__ import annotations

from app.config import get_database_url, get_sqlite_path
from integrations.history import HistoryStore, InMemoryHistoryStore
from integrations.storage.postgres_store import PostgresHistoryStore
from integrations.storage.sqlite_store import SQLiteHistoryStore


def create_history_store() -> HistoryStore:
    """Return Postgres store when DATABASE_URL is set, otherwise SQLite."""
    database_url = get_database_url()
    if database_url:
        return PostgresHistoryStore(database_url)
    return SQLiteHistoryStore(get_sqlite_path())


__all__ = [
    "HistoryStore",
    "InMemoryHistoryStore",
    "SQLiteHistoryStore",
    "PostgresHistoryStore",
    "create_history_store",
]
