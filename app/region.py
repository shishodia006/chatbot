"""Region selection for India vs international product catalogs."""

from __future__ import annotations

import re
from typing import Literal

Region = Literal["ind", "int"]

REGION_PROMPT = (
    "Welcome to the Automat Product Assistant.\n\n"
    "Are you looking for **India (local)** or **international (global)** products?\n\n"
    "Reply with **India** or **International** (you can also say *local* or *global*)."
)

REGION_INVALID = (
    "Please choose a catalog:\n\n"
    "- **India** / local — Indian product listings\n"
    "- **International** / global — global product listings"
)

REGION_LABELS: dict[Region, str] = {
    "ind": "India (local)",
    "int": "International (global)",
}


def region_confirmation(region: Region) -> str:
    label = REGION_LABELS[region]
    return (
        f"Thanks! I'll use the **{label}** catalog from now on.\n\n"
        "Ask about SKUs, product names, categories, specs, or applications."
    )


def parse_region_choice(text: str) -> Region | None:
    normalized = re.sub(r"[^a-z0-9]+", " ", text.lower()).strip()
    if not normalized:
        return None

    india_tokens = {
        "india",
        "indian",
        "local",
        "domestic",
        "ind",
        "1",
    }
    intl_tokens = {
        "international",
        "global",
        "intl",
        "export",
        "int",
        "2",
    }

    words = set(normalized.split())
    if words & india_tokens and not words & intl_tokens:
        return "ind"
    if words & intl_tokens and not words & india_tokens:
        return "int"

    if normalized in india_tokens:
        return "ind"
    if normalized in intl_tokens:
        return "int"
    return None
