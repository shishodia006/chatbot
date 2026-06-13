from __future__ import annotations

from app.catalog_service import CatalogService
from integrations.history import HistoryStore
from integrations.message_utils import split_message
from integrations.messaging_adapter import MessagingAdapter
from integrations.storage import create_history_store

TELEGRAM_MAX_MESSAGE_LENGTH = 4096


class TelegramAdapter(MessagingAdapter):
    def __init__(
        self,
        catalog: CatalogService,
        history_store: HistoryStore | None = None,
    ) -> None:
        store = history_store or create_history_store()
        super().__init__(catalog, store, channel="telegram")


__all__ = ["TelegramAdapter", "split_message", "TELEGRAM_MAX_MESSAGE_LENGTH"]
