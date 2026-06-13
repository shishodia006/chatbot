"""Run the Automat chatbot on WhatsApp via Meta Graph API (webhook server)."""

from __future__ import annotations

import json
import logging
import sys
from contextlib import asynccontextmanager
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Query, Request, Response

from app.catalog_service import CatalogService
from app.config import (
    get_database_url,
    get_gemini_api_key,
    get_port,
    get_whatsapp_access_token,
    get_whatsapp_app_secret,
    get_whatsapp_phone_number_id,
    get_whatsapp_verify_token,
    is_development,
    is_production,
)
from integrations.message_utils import split_message
from integrations.meta_client import MetaWhatsAppClient
from integrations.whatsapp import WHATSAPP_MAX_MESSAGE_LENGTH, WhatsAppAdapter
from integrations.whatsapp_webhook import (
    parse_inbound_messages,
    verify_webhook_signature,
)

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not get_gemini_api_key():
        logger.error("GEMINI_API_KEY is not set")
        sys.exit(1)

    if is_production() and not get_database_url():
        logger.warning("DATABASE_URL not set — using SQLite for conversation history")

    client = MetaWhatsAppClient()
    if is_production() and not client.configured:
        logger.error(
            "WHATSAPP_ACCESS_TOKEN and WHATSAPP_PHONE_NUMBER_ID are required in production"
        )
        sys.exit(1)

    catalog = CatalogService()
    adapter = WhatsAppAdapter(catalog)
    app.state.catalog = catalog
    app.state.adapter = adapter
    app.state.whatsapp_client = client

    logger.info(
        "WhatsApp server ready (dev=%s, ind=%s, int=%s products)",
        is_development(),
        catalog.catalog_size("ind"),
        catalog.catalog_size("int"),
    )
    yield


app = FastAPI(title="Automat WhatsApp Bot", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/webhook")
async def verify_webhook(
    hub_mode: str = Query(alias="hub.mode", default=""),
    hub_verify_token: str = Query(alias="hub.verify_token", default=""),
    hub_challenge: str = Query(alias="hub.challenge", default=""),
) -> Response:
    """Meta webhook verification handshake."""
    expected_token = get_whatsapp_verify_token()
    if not expected_token:
        raise HTTPException(status_code=500, detail="WHATSAPP_VERIFY_TOKEN is not configured")

    if hub_mode == "subscribe" and hub_verify_token == expected_token:
        logger.info("Webhook verified by Meta")
        return Response(content=hub_challenge, media_type="text/plain")

    logger.warning("Webhook verification failed")
    raise HTTPException(status_code=403, detail="Verification failed")


@app.post("/webhook")
async def receive_webhook(request: Request) -> dict[str, str]:
    """Receive inbound WhatsApp messages from Meta."""
    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")

    if not verify_webhook_signature(payload, signature, get_whatsapp_app_secret()):
        raise HTTPException(status_code=403, detail="Invalid signature")

    try:
        body = json.loads(payload)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON") from exc

    adapter: WhatsAppAdapter = request.app.state.adapter
    client: MetaWhatsAppClient = request.app.state.whatsapp_client

    if not client.configured:
        logger.error("WhatsApp client not configured — cannot send replies")
        return {"status": "ignored"}

    for inbound in parse_inbound_messages(body):
        if inbound.message_id:
            try:
                client.mark_read(inbound.message_id)
            except Exception:
                logger.debug("mark_read failed for %s", inbound.message_id, exc_info=True)

        reply = adapter.handle_incoming(inbound.from_number, inbound.text)
        for chunk in split_message(reply, max_len=WHATSAPP_MAX_MESSAGE_LENGTH):
            try:
                client.send_text(inbound.from_number, chunk)
            except Exception:
                logger.exception("Failed to send reply to %s", inbound.from_number)

    return {"status": "ok"}


@app.post("/dev/simulate")
async def dev_simulate(request: Request) -> dict[str, Any]:
    """Local testing without Meta webhook — does not send WhatsApp messages."""
    if not is_development():
        raise HTTPException(status_code=404, detail="Not found")

    body = await request.json()
    phone = body.get("phone") or body.get("from")
    text = body.get("text")
    if not phone or not text:
        raise HTTPException(status_code=400, detail='Provide JSON: {"phone":"...", "text":"..."}')

    adapter: WhatsAppAdapter = request.app.state.adapter
    reply = adapter.handle_incoming(str(phone), str(text).strip())
    return {"phone": phone, "reply": reply}


def main() -> None:
    if not get_whatsapp_access_token() or not get_whatsapp_phone_number_id():
        print(
            "WhatsApp credentials missing. Add to .env:\n"
            "  WHATSAPP_ACCESS_TOKEN=...\n"
            "  WHATSAPP_PHONE_NUMBER_ID=...\n"
            "  WHATSAPP_VERIFY_TOKEN=... (any secret string for webhook setup)",
            file=sys.stderr,
        )
        sys.exit(1)

    uvicorn.run(
        "run_whatsapp:app",
        host="0.0.0.0",
        port=get_port(),
        reload=is_development(),
    )


if __name__ == "__main__":
    main()
