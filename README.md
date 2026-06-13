# Automat Product Chatbot

AI assistant for Automat Irrigation product catalogs (India and International), powered by Google Gemini.

## Features

- Product Q&A from catalog JSON (SKUs, specs, categories)
- Region selection: India (local) or International (global)
- **Streamlit** — local web demo
- **Telegram** — messaging bot with persistent history
- **WhatsApp** — Meta Graph API webhook bot with persistent history
- **Supabase** — conversation storage (optional SQLite for local dev)

## Setup

```bash
python -m venv venv
venv\Scripts\activate        # Windows
pip install -r requirements.txt
copy .env.example .env       # Add GEMINI_API_KEY
```

## Run Streamlit demo

```bash
streamlit run run_app.py
```

Uses in-browser session history only (no database).

## Deploy the web app on Streamlit Community Cloud

1. Push the project to GitHub.
2. Open [share.streamlit.io](https://share.streamlit.io/) and sign in with GitHub.
3. Select **Create app** and enter:
   - Repository: `shishodia006/chatbot`
   - Branch: `main`
   - Main file path: `run_app.py`
4. Open **Advanced settings** and add these secrets:

   ```toml
   GEMINI_API_KEY = "your_gemini_api_key"
   GEMINI_MODEL = "gemini-3.5-flash"
   ```

5. Choose Python 3.12 and click **Deploy**.

Do not commit `.env` or `.streamlit/secrets.toml`. Root-level Streamlit secrets
are exposed to the app as environment variables, so the existing configuration
works without code changes.

## Run Telegram bot

```bash
# Add TELEGRAM_BOT_TOKEN to .env
python run_telegram.py
```

## Run WhatsApp bot (Meta Graph API)

Add to `.env`:

```env
WHATSAPP_ACCESS_TOKEN=your_permanent_token
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id
WHATSAPP_BUSINESS_ACCOUNT_ID=your_waba_id
WHATSAPP_VERIFY_TOKEN=any_secret_string
WHATSAPP_APP_SECRET=your_app_secret
ENV=development
```

Start the webhook server:

```bash
python run_whatsapp.py
```

### Meta webhook setup

1. Expose your server publicly (e.g. ngrok: `ngrok http 8000`)
2. In Meta App Dashboard → WhatsApp → Configuration:
   - **Callback URL:** `https://your-domain/webhook`
   - **Verify token:** same value as `WHATSAPP_VERIFY_TOKEN`
3. Subscribe to the **messages** field

### Local testing without Meta

With `ENV=development`, simulate a conversation:

```powershell
Invoke-RestMethod -Method POST -Uri http://localhost:8000/dev/simulate `
  -ContentType "application/json" `
  -Body '{"phone":"919876543210","text":"India"}'
```

This runs the full chatbot flow but does **not** send WhatsApp messages.

### Database

| Config | Storage |
|--------|---------|
| `DATABASE_URL` set | Supabase Postgres |
| Not set | Local SQLite at `data/conversations.db` |

Tables are created automatically on first message.

## Environment variables

| Variable | Required | Notes |
|----------|----------|-------|
| `GEMINI_API_KEY` | Yes | Powers all chat responses |
| `TELEGRAM_BOT_TOKEN` | Telegram only | From @BotFather |
| `WHATSAPP_ACCESS_TOKEN` | WhatsApp only | Permanent System User token |
| `WHATSAPP_PHONE_NUMBER_ID` | WhatsApp only | From Meta API Setup |
| `WHATSAPP_BUSINESS_ACCOUNT_ID` | Optional | WABA ID (for reference) |
| `WHATSAPP_VERIFY_TOKEN` | WhatsApp only | Your chosen webhook secret |
| `WHATSAPP_APP_SECRET` | Recommended | Validates webhook signatures |
| `WHATSAPP_API_VERSION` | Optional | Default: `v21.0` |
| `DATABASE_URL` | Optional | Supabase connection string |
| `ENV` | Optional | `development` or `production` |
| `PORT` | Optional | Default: `8000` |
| `GEMINI_MODEL` | Optional | Default: `gemini-3.5-flash` |

## Project structure

```
app/                  # Chatbot core, Streamlit UI, config
integrations/         # Telegram/WhatsApp adapters, Meta client, storage
Data/extracted/       # Product catalog JSON
run_app.py            # Streamlit entry point
run_telegram.py       # Telegram bot entry point
run_whatsapp.py       # WhatsApp webhook server
```
