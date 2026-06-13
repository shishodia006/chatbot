from __future__ import annotations

from abc import ABC, abstractmethod

from app.chatbot import AutomatChatbot, ChatMessage


class ChannelAdapter(ABC):
    """Base class for messaging channels (Telegram, WhatsApp, etc.)."""

    def __init__(self, chatbot: AutomatChatbot) -> None:
        self.chatbot = chatbot

    @abstractmethod
    def handle_incoming(self, user_id: str, text: str) -> str:
        """Process an inbound message and return the bot reply."""

    def get_history(self, user_id: str) -> list[ChatMessage]:
        return []

    def save_turn(self, user_id: str, user_text: str, assistant_text: str) -> None:
        pass
