from __future__ import annotations

from app.catalog_service import CatalogService
from app.chatbot import ChatMessage
from app.region import (
    REGION_INVALID,
    REGION_PROMPT,
    parse_region_choice,
    region_confirmation,
)
from integrations.base import ChannelAdapter
from integrations.history import HistoryStore


class MessagingAdapter(ChannelAdapter):
    """Shared region-selection and Q&A flow for Telegram and WhatsApp."""

    def __init__(
        self,
        catalog: CatalogService,
        history_store: HistoryStore,
        channel: str,
    ) -> None:
        self.catalog = catalog
        self._history = history_store
        self._channel = channel
        super().__init__(self.catalog.get_chatbot("ind"))

    def reset_user(self, user_id: str) -> None:
        self._history.clear(user_id)

    def get_history(self, user_id: str) -> list[ChatMessage]:
        return self._history.get(user_id)

    def save_turn(self, user_id: str, user_text: str, assistant_text: str) -> None:
        self._history.add_turn(user_id, user_text, assistant_text)

    def handle_incoming(self, user_id: str, text: str) -> str:
        try:
            self._history.ensure_session(user_id, self._channel)
            region = self._history.get_region(user_id)
            if region is None:
                chosen = parse_region_choice(text)
                if chosen is None:
                    return REGION_INVALID
                self._history.set_region(user_id, chosen)
                return region_confirmation(chosen)

            chatbot = self.catalog.get_chatbot(region)
            history = self.get_history(user_id)
            reply = chatbot.answer(text, history=history)
            self.save_turn(user_id, text, reply)
            return reply
        except Exception as exc:
            return f"Something went wrong: {exc}"

    def welcome_message(self) -> str:
        return REGION_PROMPT
