from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import (
    get_whatsapp_access_token,
    get_whatsapp_api_version,
    get_whatsapp_phone_number_id,
)

logger = logging.getLogger(__name__)


class MetaWhatsAppClient:
    """Send messages via Meta WhatsApp Cloud API (Graph API)."""

    def __init__(
        self,
        access_token: str | None = None,
        phone_number_id: str | None = None,
        api_version: str | None = None,
    ) -> None:
        self._token = access_token or get_whatsapp_access_token()
        self._phone_number_id = phone_number_id or get_whatsapp_phone_number_id()
        self._api_version = api_version or get_whatsapp_api_version()

    @property
    def configured(self) -> bool:
        return bool(self._token and self._phone_number_id)

    def _messages_url(self) -> str:
        if not self._phone_number_id:
            raise RuntimeError("WHATSAPP_PHONE_NUMBER_ID is not set")
        return (
            f"https://graph.facebook.com/{self._api_version}"
            f"/{self._phone_number_id}/messages"
        )

    def _headers(self) -> dict[str, str]:
        if not self._token:
            raise RuntimeError("WHATSAPP_ACCESS_TOKEN is not set")
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    def send_text(self, to: str, text: str) -> dict[str, Any]:
        """Send a text message to a WhatsApp user (digits only, with country code)."""
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "text",
            "text": {"body": text},
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                self._messages_url(),
                json=payload,
                headers=self._headers(),
            )
        if response.is_error:
            logger.error(
                "Meta send_text failed (%s): %s",
                response.status_code,
                response.text,
            )
            response.raise_for_status()
        return response.json()

    def mark_read(self, message_id: str) -> dict[str, Any]:
        """Mark an inbound message as read."""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id,
        }
        with httpx.Client(timeout=30.0) as client:
            response = client.post(
                self._messages_url(),
                json=payload,
                headers=self._headers(),
            )
        if response.is_error:
            logger.warning(
                "Meta mark_read failed (%s): %s",
                response.status_code,
                response.text,
            )
            response.raise_for_status()
        return response.json()
