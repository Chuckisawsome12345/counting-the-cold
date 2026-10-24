"""Telegram bot: message a place or share a location, get the chill and heat summary back.

Free alternative to SMS (no carrier registration). Replies ride on the webhook response itself
(Telegram's "answer the webhook with a method" pattern), so no outbound call per message.
Only Telegram knows the webhook secret, which is derived from the bot token.

Setup: create a bot with @BotFather, set TELEGRAM_BOT_TOKEN on the backend, redeploy, then open
GET /api/telegram/setup once to register the webhook.
"""
import hashlib
import hmac
from datetime import date

import httpx
from fastapi import APIRouter, HTTPException, Request

from app import config
from app.routes import sms

router = APIRouter(prefix="/api/telegram", tags=["telegram"])

API = "https://api.telegram.org"
HELP = (
    "Counting the Cold: your orchard's chill and heat, not a station's.\n\n"
    "Share your orchard's location (paperclip > Location), or type it as lat,lon "
    "(e.g. 39.64,-121.79), or send DURHAM, DAVIS or PARLIER."
)


def webhook_secret(token: str) -> str:
    """Secret Telegram echoes in X-Telegram-Bot-Api-Secret-Token; derived so there's no second env var."""
    return hashlib.sha256(f"counting-the-cold:{token}".encode()).hexdigest()


@router.post("", summary="Telegram webhook: a place or a shared location in, a summary out")
async def telegram(request: Request) -> dict:
    token = _token()
    given = request.headers.get("x-telegram-bot-api-secret-token", "")
    if not hmac.compare_digest(given, webhook_secret(token)):
        raise HTTPException(403, "invalid Telegram secret")
    update = await request.json()
    message = update.get("message") or update.get("edited_message")
    if not message:
        return {}  # other update types: acknowledge and ignore
    return {"method": "sendMessage", "chat_id": message["chat"]["id"], "text": reply_for_message(message, date.today())}


def reply_for_message(message: dict, today: date) -> str:
    if "location" in message:
        loc = message["location"]
        return sms.reply_for_spot(None, loc["latitude"], loc["longitude"], today)
    text = message.get("text", "").strip()
    command = text.lstrip("/").split("@")[0].lower()  # "/durham@SomeBot" -> "durham"
    if command in {"", "start", "help"}:
        return HELP
    if command in sms.PLACES:
        text = command
    reply = sms.reply_for(text, today)
    return HELP if reply in (None, sms.HELP) else reply


@router.get("/setup", summary="Register this backend as the bot's webhook (open once after deploying)")
def setup(request: Request) -> dict:
    token = _token()
    url = config.TELEGRAM_WEBHOOK_URL or f"https://{request.url.netloc}/api/telegram"
    result = telegram_api(token, "setWebhook", {
        "url": url,
        "secret_token": webhook_secret(token),
        "allowed_updates": ["message", "edited_message"],
        "drop_pending_updates": True,
    })
    telegram_api(token, "setMyCommands", {"commands": [
        {"command": "help", "description": "How to use the bot"},
        {"command": "durham", "description": "Orchard near the closed Durham station"},
        {"command": "davis", "description": "Davis"},
        {"command": "parlier", "description": "Parlier"},
    ]})
    return {"ok": bool(result.get("ok")), "webhook": url, "telegram": result.get("description", "")}


def telegram_api(token: str, method: str, payload: dict) -> dict:
    try:
        return httpx.post(f"{API}/bot{token}/{method}", json=payload, timeout=15).json()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Couldn't reach Telegram ({type(e).__name__})") from e


def _token() -> str:
    if not config.TELEGRAM_BOT_TOKEN:
        raise HTTPException(503, "The Telegram bot isn't configured: set TELEGRAM_BOT_TOKEN on the backend.")
    return config.TELEGRAM_BOT_TOKEN
