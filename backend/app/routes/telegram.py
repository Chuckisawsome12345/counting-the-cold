"""Telegram bot: message a place or share a location, get the chill and heat summary back.

Free alternative to SMS (no carrier registration). Replies ride on the webhook response itself
(Telegram's "answer the webhook with a method" pattern), so no outbound call per message.
Only Telegram knows the webhook secret, which is derived from the bot token.

Setup: create a bot with @BotFather, set TELEGRAM_BOT_TOKEN on the backend, redeploy, then open
GET /api/telegram/setup once to register the webhook.
"""
import hashlib
import hmac
import logging
from datetime import date

import httpx
from fastapi import APIRouter, HTTPException, Query, Request

from app import config
from app.schemas import BotPreviewResponse
from app.routes import sms

router = APIRouter(prefix="/api/telegram", tags=["telegram"])
log = logging.getLogger("telegram")

API = "https://api.telegram.org"
HELP = (
    "Counting the Cold: your orchard's chill and heat, not a station's.\n\n"
    "Share your orchard's location (paperclip > Location), or type it as lat,lon "
    "(e.g. 39.64,-121.79), or send DURHAM, DAVIS or PARLIER.\n\n"
    "For what to watch for, send /suggest with a place: /suggest durham or /suggest 39.64,-121.79"
)
SUGGEST_USAGE = "Add a place after /suggest, e.g. /suggest durham or /suggest 39.64,-121.79"
DISCLAIMER = ("General pointers from this data, not a farming recommendation. "
              "For decisions, check with your UC Cooperative Extension farm advisor.")
UC_IPM = "https://ipm.ucanr.edu"
BLOOM_MONTHS = {2, 3, 4}  # when a freezing night matters most for almonds and stone fruit
FREEZE_F = 32.0
HEAT_F = 100.0
PACE_PCT = 15.0  # how far from the 10-season median counts as "behind" or "ahead"


def webhook_secret(token: str) -> str:
    """Secret Telegram echoes in X-Telegram-Bot-Api-Secret-Token; derived so there's no second env var."""
    return hashlib.sha256(f"counting-the-cold:{token}".encode()).hexdigest()


@router.post("", summary="Telegram webhook: a place or a shared location in, a summary out")
async def telegram(request: Request) -> dict:
    token = _token()
    given = request.headers.get("x-telegram-bot-api-secret-token", "")
    if not hmac.compare_digest(given, webhook_secret(token)):
        log.warning("telegram webhook rejected: %s secret", "wrong" if given else "missing")
        raise HTTPException(403, "invalid Telegram secret")
    update = await request.json()
    message = update.get("message") or update.get("edited_message")
    if not message:
        log.info("telegram update ignored: %s", ", ".join(k for k in update if k != "update_id"))
        return {}  # other update types: acknowledge and ignore
    reply = reply_for_message(message, date.today())
    # Just the kind of message, never its text or location.
    kind = "location" if "location" in message else (message.get("text") or "").split(" ")[0].split("@")[0][:20] or "other"
    log.info("telegram update answered: %s -> %d chars", kind if kind.startswith("/") or kind == "location" else "text", len(reply))
    return {"method": "sendMessage", "chat_id": message["chat"]["id"], "text": reply}


def reply_for_message(message: dict, today: date) -> str:
    if "location" in message:
        loc = message["location"]
        return sms.reply_for_spot(None, loc["latitude"], loc["longitude"], today, describe)
    text = message.get("text", "").strip()
    word, _, rest = text.partition(" ")
    command = word.lstrip("/").split("@")[0].lower()  # "/durham@SomeBot" -> "durham"
    if command in {"", "start", "help"}:
        return HELP
    if command in {"suggest", "suggestions", "advice"}:
        place = sms.parse_place(rest)
        return sms.reply_for_spot(*place, today, suggest) if place else SUGGEST_USAGE
    if command in sms.PLACES:
        text = command
    reply = sms.reply_for(text, today, describe)
    if reply in (None, sms.HELP):
        return HELP
    if reply == sms.NOT_UNDERSTOOD:
        return "Sorry, I didn't get that.\n\n" + HELP
    return reply


def describe(p: dict, name: str | None) -> str:
    """The fuller Telegram reply: every measure, how it compares with normal, what's next, and where to look."""
    s, t, st = p["season"], p["totals"], p["settings"]
    where = name or f"Orchard near {p['nearest_station']['name']}"
    status = "complete" if s["complete"] else f"as of {_day(s['as_of'])}"
    lines = [f"{where} · {s['label']} season ({status})", "", "Chill (winter cold)"]
    lines.append(_metric_line(p, "chill_portions", "Chill portions", s["portions_start"]))
    lines.append(_metric_line(p, "chill_hours", "Chill hours", s["hours_start"]))
    lines.append(_metric_line(p, "utah_units", "Utah units", s["hours_start"]))
    lines += ["", "Heat"]
    lines.append(_metric_line(p, "gdd", "Growing degree days", s["gdd_start"], f"{st['crop']}, base {st['gdd_base_f']:g}°F"))

    extra = []
    if p["forecast"]:
        gains = {m: p["forecast"]["plus14"][m] - t[m] for m in t}
        parts = [f"+{gains['chill_portions']:.0f} chill portions", f"+{gains['chill_hours']:.0f} chill hours"]
        if gains["gdd"] > 0:
            parts.append(f"+{gains['gdd']:.0f} GDD")
        extra.append("Next 14 days: " + ", ".join(parts))
    clim = (p.get("climatology") or {}).get("chill_portions")
    if clim and not _not_calculated(p, "chill_portions"):
        extra.append(f"Likely end of season: about {clim['p50']:.0f} chill portions (range {clim['p10']:.0f} to {clim['p90']:.0f})")
    if not s["complete"] and p["history"]:
        last = p["history"][-1]["totals"]
        parts = [f"{last[m]:,.0f} {label}" for m, label in (("chill_portions", "chill portions"), ("chill_hours", "chill hours"), ("utah_units", "Utah units"), ("gdd", "GDD")) if last[m] > 0]
        if parts:
            extra.append(f"Last season ({p['history'][-1]['season']}): " + ", ".join(parts))
    if extra:
        lines += [""] + extra

    lines.append("")
    err = p["correction"]["expected_error"]
    if err:
        lines.append(f"Typical error vs real stations: ±{err['chill_portions']:.1f} chill portions, ±{err['chill_hours']:.0f} chill hours")
    ns = p["nearest_station"]
    lines.append(f"Nearest CIMIS station: {ns['name']} #{ns['id']}{'' if ns['active'] else ' (closed)'}, {ns['distance_km']:.1f} km away")
    if p.get("mock"):
        lines.append("(Sample data while the live pipeline finishes.)")
    if p["quality"].get("stale"):
        lines.append("(Cached data: live weather is unavailable right now.)")
    lines.append(f"Charts and details: {config.FRONTEND_URL}")
    lines.append(f"What to watch for: /suggest {_place_arg(p, name)}")
    return "\n".join(lines)


def suggest(p: dict, name: str | None) -> str:
    """Data-driven pointers, each tied to a number shown in the summary. No prescriptions."""
    s, t = p["season"], p["totals"]
    where = name or f"Orchard near {p['nearest_station']['name']}"
    tips = []

    # Chill pace
    hours_start = date.fromisoformat(s["hours_start"])
    if not s["complete"] and hours_start > date.fromisoformat(s["as_of"]):
        if p["history"]:
            last = p["history"][-1]
            tips.append(f"Chill hours start counting {_day(s['hours_start'])}. Last winter ({last['season']}) this orchard got "
                        f"{last['totals']['chill_hours']:,.0f} chill hours; check back weekly to see if this winter keeps pace.")
    else:
        metric = "chill_hours" if _not_calculated(p, "chill_portions") else "chill_portions"
        label = "Chill hours are" if metric == "chill_hours" else "Chill portions are"
        pct = sms.vs_normal(p, metric)
        when = "for this point in the season" if not s["complete"] else "for a full season"
        if pct is not None and pct <= -PACE_PCT:
            tips.append(f"{label} running {abs(pct):.0f}% behind a typical year {when}. Low chill can delay bloom and make it "
                        "uneven: watch bloom timing closely and ask your farm advisor about options for low-chill years.")
        elif pct is not None and pct >= PACE_PCT:
            tips.append(f"{label} running {pct:.0f}% ahead of a typical year {when}, which favors an even bloom.")
        elif pct is not None:
            tips.append(f"{label} close to a typical year {when} ({pct:+.0f}%).")

    # Frost and heat in the 14-day forecast
    days = (p["forecast"] or {}).get("daily", [])
    frost = [d for d in days if d["tmin"] is not None and d["tmin"] <= FREEZE_F and date.fromisoformat(d["date"]).month in BLOOM_MONTHS]
    if frost:
        nights = ", ".join(f"{_day(d['date'])} ({d['tmin']:.0f}°F)" for d in frost[:4])
        tips.append(f"Freezing nights in the forecast during bloom season: {nights}. "
                    "If trees are blooming or leafing out, plan frost protection.")
    heat = [d for d in days if d["tmax"] is not None and d["tmax"] >= HEAT_F]
    if heat:
        hot = ", ".join(f"{_day(d['date'])} ({d['tmax']:.0f}°F)" for d in heat[:4])
        tips.append(f"Hot days ahead: {hot}. Check irrigation before the heat arrives.")

    # Heat units and pest timing
    gdd_pct = sms.vs_normal(p, "gdd") if t["gdd"] > 0 else None
    if gdd_pct is not None and abs(gdd_pct) >= 10:
        direction = "ahead of" if gdd_pct > 0 else "behind"
        sooner = "earlier" if gdd_pct > 0 else "later"
        tips.append(f"Heat is running {abs(gdd_pct):.0f}% {direction} normal, so pest generations and harvest may come {sooner} "
                    f"than usual. UC IPM's degree-day models turn this count into monitoring dates: {UC_IPM}")
    elif t["gdd"] > 0:
        tips.append(f"Degree days drive pest timing (for almonds, navel orangeworm). Use this count with UC IPM's degree-day models: {UC_IPM}")

    if not tips:
        tips.append("Nothing stands out right now: chill and heat are near typical and the forecast has no frost or heat spikes.")
    lines = [f"Suggestions for {where} · {s['label']} season", ""]
    lines += [f"{i}. {tip}" for i, tip in enumerate(tips, 1)]
    lines += ["", DISCLAIMER]
    return "\n".join(lines)


def _place_arg(p: dict, name: str | None) -> str:
    """What to type after /suggest to get back to this place."""
    if name:
        return name.lower()
    loc = p["location"]
    return f"{loc['lat']:.2f},{loc['lon']:.2f}"


def _metric_line(p: dict, metric: str, label: str, start_iso: str, extra: str | None = None) -> str:
    s = p["season"]
    start = date.fromisoformat(start_iso)
    details = []
    if _not_calculated(p, metric):
        main = "not calculated yet"
    elif not s["complete"] and start > date.fromisoformat(s["as_of"]):
        main = "not counting yet"
        details.append(f"starts {_day(start_iso)}")
    else:
        value = f"{p['totals'][metric]:,.0f}"
        main = value if s["complete"] else f"{value} so far"
        if not s["complete"]:
            details.append(f"since {_day(start_iso)}")
        pct = sms.vs_normal(p, metric)
        if pct is not None:
            details.append("about normal" if abs(pct) < 0.5 else f"{'▲' if pct > 0 else '▼'}{abs(pct):.0f}% vs the 10-season median")
    if extra:
        details.append(extra)
    return f"• {label}: {main}" + (f" ({'; '.join(details)})" if details else "")


def _not_calculated(p: dict, metric: str) -> bool:
    """Zero now and in every past season means the model behind it isn't running yet."""
    return p["totals"][metric] == 0 and bool(p["history"]) and all(h["totals"][metric] == 0 for h in p["history"])


def _day(iso: str) -> str:
    d = date.fromisoformat(iso)
    return f"{d:%b} {d.day}"


@router.get("/preview", response_model=BotPreviewResponse,
            summary="The bot's reply to a message, without Telegram (the website's Try the bot box)")
def preview(text: str = Query("", max_length=200, description="What the user would send, e.g. durham, 39.64,-121.79, /suggest davis")) -> dict:
    return {"text": reply_for_message({"text": text}, date.today()), "bot_url": bot_url()}


_bot_url: str | None = None


def bot_url() -> str | None:
    """https://t.me/<username> for the real bot, looked up once; None if the bot isn't configured or Telegram is unreachable."""
    global _bot_url
    if _bot_url is None and config.TELEGRAM_BOT_TOKEN:
        try:
            username = telegram_api(config.TELEGRAM_BOT_TOKEN, "getMe", {}).get("result", {}).get("username")
        except HTTPException:
            username = None
        if username:
            _bot_url = f"https://t.me/{username}"
    return _bot_url


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
        {"command": "suggest", "description": "What to watch for at a place, e.g. /suggest durham"},
        {"command": "durham", "description": "Orchard near the closed Durham station"},
        {"command": "davis", "description": "Davis"},
        {"command": "parlier", "description": "Parlier"},
    ]})
    return {"ok": bool(result.get("ok")), "webhook": url, "telegram": result.get("description", "")}


@router.get("/status", summary="What Telegram reports about the webhook (last error, pending messages)")
def status() -> dict:
    info = telegram_api(_token(), "getWebhookInfo", {}).get("result", {})
    return {k: info.get(k) for k in ("url", "pending_update_count", "last_error_date", "last_error_message", "max_connections", "ip_address")}


def telegram_api(token: str, method: str, payload: dict) -> dict:
    try:
        return httpx.post(f"{API}/bot{token}/{method}", json=payload, timeout=15).json()
    except httpx.HTTPError as e:
        raise HTTPException(502, f"Couldn't reach Telegram ({type(e).__name__})") from e


def _token() -> str:
    if not config.TELEGRAM_BOT_TOKEN:
        raise HTTPException(503, "The Telegram bot isn't configured: set TELEGRAM_BOT_TOKEN on the backend.")
    return config.TELEGRAM_BOT_TOKEN
