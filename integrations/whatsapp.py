from __future__ import annotations

from app.catalog_service import CatalogService
from integrations.history import HistoryStore
from integrations.message_utils import split_message
from integrations.messaging_adapter import MessagingAdapter
from integrations.storage import create_history_store

WHATSAPP_MAX_MESSAGE_LENGTH = 4096


class WhatsAppAdapter(MessagingAdapter):
    def __init__(
        self,
        catalog: CatalogService,
        history_store: HistoryStore | None = None,
    ) -> None:
        store = history_store or create_history_store()
        super().__init__(catalog, store, channel="whatsapp")


__all__ = ["WhatsAppAdapter", "split_message", "WHATSAPP_MAX_MESSAGE_LENGTH"]
