"""Load and serve India vs international product catalogs."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from app.chatbot import AutomatChatbot
from app.config import DATA_DIR
from app.data_loader import load_product_records
from app.region import Region
from app.retriever import ProductRetriever


class CatalogService:
    def __init__(self, data_dir: Path | None = None) -> None:
        base = data_dir or DATA_DIR
        self._chatbots: dict[Region, AutomatChatbot] = {}
        self._counts: dict[Region, int] = {}
        for region in ("ind", "int"):
            records = load_product_records(base, region=region)
            self._counts[region] = len(records)
            self._chatbots[region] = AutomatChatbot(ProductRetriever(records))

    def get_chatbot(self, region: Region) -> AutomatChatbot:
        return self._chatbots[region]

    def catalog_size(self, region: Region) -> int:
        return self._counts[region]


@lru_cache(maxsize=1)
def get_catalog_service() -> CatalogService:
    return CatalogService()
