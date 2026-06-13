"""Run the Automat chatbot on Telegram (long polling)."""

from __future__ import annotations

import logging
import sys

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.catalog_service import CatalogService
from app.config import get_gemini_api_key, get_telegram_bot_token
from integrations.telegram import TelegramAdapter, split_message

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.effective_chat:
        return
    adapter: TelegramAdapter = context.application.bot_data["adapter"]
    chat_id = str(update.effective_chat.id)
    adapter.reset_user(chat_id)
    await update.message.reply_text(adapter.welcome_message())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "First reply **India** or **International** to pick a catalog, then ask "
            "about SKUs, specs, or categories. Use /start to switch region."
        )


async def on_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = update.message
    if not message or not message.text or not update.effective_chat:
        return

    adapter: TelegramAdapter = context.application.bot_data["adapter"]
    chat_id = str(update.effective_chat.id)
    text = message.text.strip()

    await message.chat.send_action("typing")
    reply = adapter.handle_incoming(chat_id, text)

    for chunk in split_message(reply):
        await message.reply_text(chunk)


async def on_non_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(
            "Please send a text message. Start with /start, then choose "
            "**India** or **International**."
        )


def main() -> None:
    if not get_gemini_api_key():
        print(
            "GEMINI_API_KEY not found. Add it to .env in the project root.\n"
            "Get a key at https://aistudio.google.com/apikey",
            file=sys.stderr,
        )
        sys.exit(1)

    token = get_telegram_bot_token()
    if not token:
        print(
            "TELEGRAM_BOT_TOKEN not found. Create a bot with @BotFather and add:\n"
            "TELEGRAM_BOT_TOKEN=your_token_here",
            file=sys.stderr,
        )
        sys.exit(1)

    catalog = CatalogService()
    adapter = TelegramAdapter(catalog)

    app = Application.builder().token(token).build()
    app.bot_data["adapter"] = adapter

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    app.add_handler(MessageHandler(~filters.TEXT, on_non_text))

    logger.info(
        "Telegram bot started (ind=%s, int=%s products)",
        catalog.catalog_size("ind"),
        catalog.catalog_size("int"),
    )
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
