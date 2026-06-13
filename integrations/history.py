from __future__ import annotations

from abc import ABC, abstractmethod

from app.chatbot import ChatMessage
from app.region import Region


class HistoryStore(ABC):
    """Persistent or in-memory conversation store keyed by user_id (phone or chat_id)."""

    @abstractmethod
    def get(self, user_id: str) -> list[ChatMessage]:
        """Return conversation history for a user."""

    @abstractmethod
    def add_turn(self, user_id: str, user_text: str, assistant_text: str) -> None:
        """Append a user/assistant turn and prune to max message cap."""

    @abstractmethod
    def clear(self, user_id: str) -> None:
        """Clear history and region for a user."""

    @abstractmethod
    def get_region(self, user_id: str) -> Region | None:
        """Return the catalog region chosen by the user, if any."""

    @abstractmethod
    def set_region(self, user_id: str, region: Region) -> None:
        """Persist the user's catalog region choice."""

    @abstractmethod
    def ensure_session(self, user_id: str, channel: str) -> None:
        """Create a session row if the user has not interacted before."""


class InMemoryHistoryStore(HistoryStore):
    """Per-user conversation history for tests and local fallback."""

    def __init__(self, max_messages: int = 12) -> None:
        self._store: dict[str, list[ChatMessage]] = {}
        self._regions: dict[str, Region] = {}
        self._channels: dict[str, str] = {}
        self._max_messages = max_messages

    def ensure_session(self, user_id: str, channel: str) -> None:
        self._channels.setdefault(user_id, channel)

    def get(self, user_id: str) -> list[ChatMessage]:
        return list(self._store.get(user_id, []))

    def clear(self, user_id: str) -> None:
        self._store.pop(user_id, None)
        self._regions.pop(user_id, None)
        self._channels.pop(user_id, None)

    def get_region(self, user_id: str) -> Region | None:
        return self._regions.get(user_id)

    def set_region(self, user_id: str, region: Region) -> None:
        self._regions[user_id] = region

    def add_turn(self, user_id: str, user_text: str, assistant_text: str) -> None:
        history = self._store.setdefault(user_id, [])
        history.extend(
            [
                ChatMessage(role="user", content=user_text),
                ChatMessage(role="assistant", content=assistant_text),
            ]
        )
        if len(history) > self._max_messages:
            self._store[user_id] = history[-self._max_messages :]
