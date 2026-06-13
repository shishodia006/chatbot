from __future__ import annotations

import hashlib
import hmac
import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class InboundMessage:
    from_number: str
    text: str
    message_id: str | None = None


def verify_webhook_signature(
    payload: bytes,
    signature_header: str | None,
    app_secret: str | None,
) -> bool:
    """Validate X-Hub-Signature-256 from Meta webhook POST."""
    if not app_secret:
        logger.warning("WHATSAPP_APP_SECRET not set — skipping signature check")
        return True
    if not signature_header or not signature_header.startswith("sha256="):
        return False

    expected = hmac.new(
        app_secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest()
    received = signature_header.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)


def parse_inbound_messages(body: dict[str, Any]) -> list[InboundMessage]:
    """Extract inbound text messages from a Meta WhatsApp webhook payload."""
    if body.get("object") != "whatsapp_business_account":
        return []

    messages: list[InboundMessage] = []
    for entry in body.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value") or {}
            for msg in value.get("messages") or []:
                if msg.get("type") != "text":
                    continue
                text_obj = msg.get("text") or {}
                body_text = text_obj.get("body")
                from_number = msg.get("from")
                if not from_number or not body_text:
                    continue
                messages.append(
                    InboundMessage(
                        from_number=str(from_number),
                        text=str(body_text).strip(),
                        message_id=msg.get("id"),
                    )
                )
    return messages
