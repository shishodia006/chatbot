from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "Data" / "extracted"

load_dotenv(PROJECT_ROOT / ".env")


def get_gemini_api_key() -> str | None:
    return os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")


def get_gemini_model() -> str:
    return os.getenv("GEMINI_MODEL", "gemini-3.5-flash")


def get_telegram_bot_token() -> str | None:
    return os.getenv("TELEGRAM_BOT_TOKEN")


def normalize_database_url(url: str) -> str:
    """Normalize Postgres URLs for Supabase and other providers."""
    if url.startswith("postgres://"):
        url = "postgresql://" + url[len("postgres://") :]

    parsed = urlparse(url)
    host = parsed.hostname or ""
    query = parse_qs(parsed.query)

    if "supabase.co" in host and "sslmode" not in query:
        query["sslmode"] = ["require"]

    normalized_query = urlencode({k: v[0] for k, v in query.items()})
    return urlunparse(parsed._replace(query=normalized_query))


def get_database_url() -> str | None:
    raw = os.getenv("DATABASE_URL") or os.getenv("SUPABASE_DB_URL")
    if not raw:
        return None
    return normalize_database_url(raw)


def get_sqlite_path() -> Path:
    raw = os.getenv("SQLITE_PATH", "data/conversations.db")
    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path


def get_whatsapp_access_token() -> str | None:
    return os.getenv("WHATSAPP_ACCESS_TOKEN")


def get_whatsapp_phone_number_id() -> str | None:
    return os.getenv("WHATSAPP_PHONE_NUMBER_ID")


def get_whatsapp_business_account_id() -> str | None:
    return os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID")


def get_whatsapp_verify_token() -> str | None:
    return os.getenv("WHATSAPP_VERIFY_TOKEN")


def get_whatsapp_app_secret() -> str | None:
    return os.getenv("WHATSAPP_APP_SECRET")


def get_whatsapp_api_version() -> str:
    return os.getenv("WHATSAPP_API_VERSION", "v21.0")


def get_port() -> int:
    return int(os.getenv("PORT", "8000"))


def get_env() -> str:
    return os.getenv("ENV", "development").lower()


def is_development() -> bool:
    return get_env() == "development"


def is_production() -> bool:
    return get_env() == "production"
