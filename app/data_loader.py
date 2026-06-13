from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from app.config import DATA_DIR

PRODUCTS_IND_FILE = "products_ind.json"
PRODUCTS_INT_FILE = "products_int.json"

REGION_FILES = {
    "ind": PRODUCTS_IND_FILE,
    "int": PRODUCTS_INT_FILE,
}

DEFAULT_SOURCES = {
    "ind": "www.automatworld.in/india",
    "int": "www.automatworld.in/global",
}

SKU_PREFIX_RE = re.compile(
    r"^((?:HT|AQ)[\w-]+(?:\s*\([^)]+\))?)",
    re.IGNORECASE,
)


@dataclass
class ProductRecord:
    sku: str | None = None
    name: str | None = None
    category: str = ""
    features: dict[str, str] | None = None
    applications: list[str] | None = None
    source: str = ""
    page: int = 0

    def to_context_block(self) -> str:
        lines: list[str] = []
        if self.sku:
            lines.append(f"SKU: {self.sku}")
        if self.name:
            lines.append(f"Name: {self.name}")
        if not lines:
            lines.append("Product: (unknown)")
        lines.append(f"Category: {self.category}")
        if self.applications:
            lines.append("Applications:")
            for app in self.applications:
                lines.append(f"  - {app}")
        if self.features:
            lines.append("Features:")
            for feat_name, detail in self.features.items():
                lines.append(f"  - {feat_name}: {detail}")
        if self.page:
            lines.append(f"Catalog page: {self.page}")
        if self.source:
            lines.append(f"Source: {self.source}")
        return "\n".join(lines)

    @property
    def identifier(self) -> str:
        return self.sku or self.name or ""


def _parse_features(raw: object) -> dict[str, str] | None:
    if raw is None:
        return None
    if isinstance(raw, str):
        text = raw.strip()
        return {"Detail": text} if text else None
    if not isinstance(raw, dict):
        return None
    cleaned = {str(k): str(v).strip() for k, v in raw.items() if str(v).strip()}
    return cleaned or None


def _parse_applications(raw: object) -> list[str] | None:
    if raw is None:
        return None
    if isinstance(raw, list):
        cleaned = [str(a).strip() for a in raw if a is not None and str(a).strip()]
        return cleaned or None
    text = str(raw).strip()
    if not text:
        return None
    parts = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    return parts if parts else [text]


def _optional_str(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _split_sku_name(combined: str) -> tuple[str | None, str | None]:
    combined = combined.strip()
    if not combined:
        return None, None
    match = SKU_PREFIX_RE.match(combined)
    if match:
        sku = match.group(1).strip()
        remainder = combined[match.end() :].strip()
        return sku, remainder or sku
    return None, combined


def _resolve_identity(item: dict) -> tuple[str | None, str | None]:
    sku = _optional_str(item.get("SKU", item.get("sku")))
    name = _optional_str(item.get("Name", item.get("name")))
    combined = _optional_str(item.get("SKU/Name", item.get("sku_name")))
    if combined:
        parsed_sku, parsed_name = _split_sku_name(combined)
        sku = sku or parsed_sku
        name = name or parsed_name
    return sku, name


def _load_json_products(path: Path) -> list[ProductRecord]:
    if not path.exists():
        return []
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        return []

    records: list[ProductRecord] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        sku, name = _resolve_identity(item)
        if not sku and not name:
            continue
        meta = item.get("_meta") or {}
        category = item.get("Category") or item.get("category")
        category_str = "" if category is None else str(category).strip()
        default_source = ""
        for region, filename in REGION_FILES.items():
            if path.name == filename:
                default_source = DEFAULT_SOURCES[region]
                break

        records.append(
            ProductRecord(
                sku=sku,
                name=name,
                category=category_str,
                features=_parse_features(item.get("Features", item.get("features"))),
                applications=_parse_applications(
                    item.get("Applications", item.get("applications"))
                ),
                source=str(
                    meta.get("source") or item.get("source") or default_source
                ).strip(),
                page=int(meta.get("page") or item.get("page") or 0),
            )
        )
    return records


def load_product_records(
    data_dir: Path | None = None,
    *,
    region: str = "ind",
) -> list[ProductRecord]:
    base = data_dir or DATA_DIR
    filename = REGION_FILES.get(region, PRODUCTS_IND_FILE)
    return _load_json_products(base / filename)
