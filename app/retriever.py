from __future__ import annotations

import re
from dataclasses import dataclass

from app.data_loader import ProductRecord


@dataclass
class SearchResult:
    record: ProductRecord
    score: float


def _tokenize(text: str) -> set[str]:
    return {t for t in re.findall(r"[a-z0-9]+", text.lower()) if len(t) > 1}


class ProductRetriever:
    def __init__(self, records: list[ProductRecord]) -> None:
        self.records = records

    def search(self, query: str, top_k: int = 8) -> list[ProductRecord]:
        query_tokens = _tokenize(query)
        query_upper = query.upper()
        results: list[SearchResult] = []

        for record in self.records:
            blob = record.to_context_block()
            blob_tokens = _tokenize(blob)
            overlap = len(query_tokens & blob_tokens)

            score = float(overlap)
            if record.sku and record.sku.upper() in query_upper:
                score += 20.0
            if record.name and record.name.lower() in query.lower():
                score += 15.0
            for token in query_tokens:
                if len(token) >= 4 and token in blob.lower():
                    score += 0.5

            category_tokens = _tokenize(record.category)
            score += len(query_tokens & category_tokens) * 2.0

            if score > 0:
                results.append(SearchResult(record=record, score=score))

        results.sort(key=lambda r: r.score, reverse=True)
        seen: set[str] = set()
        picked: list[ProductRecord] = []

        for item in results:
            key = item.record.identifier or item.record.to_context_block()[:120]
            if key in seen:
                continue
            seen.add(key)
            picked.append(item.record)
            if len(picked) >= top_k:
                break

        if not picked and self.records:
            # Broad questions (e.g. "what do you sell?") — return category samples
            picked = self.records[:top_k]

        return picked

    def build_context(self, query: str, top_k: int = 8) -> str:
        hits = self.search(query, top_k=top_k)
        if not hits:
            return "No matching catalog entries were found."
        blocks = [f"[{i + 1}]\n{r.to_context_block()}" for i, r in enumerate(hits)]
        return "\n\n".join(blocks)
