"""Text-message access (Twilio webhook): text a location, get a one-text chill and heat summary back.

Twilio POSTs form-encoded fields (Body, From, ...) and reads our TwiML reply, so no Twilio
library is needed. Replies stay plain ASCII and at most 160 characters: one SMS segment.
When TWILIO_AUTH_TOKEN is set, requests must carry a valid X-Twilio-Signature.
"""
import base64
import hashlib
import hmac
import re
from datetime import date
from urllib.parse import parse_qsl
from xml.sax.saxutils import escape

from fastapi import APIRouter, HTTPException, Request, Response

from app import config
from app.routes.point import point

router = APIRouter(prefix="/api", tags=["sms"])

MAX_LEN = 160
HELP = "Counting the Cold: text your orchard as lat,lon (e.g. 39.64,-121.79) or DURHAM, DAVIS or PARLIER to get its chill and heat so far."
NOT_UNDERSTOOD = "Sorry, I didn't get that. Text your orchard as lat,lon, e.g. 39.64,-121.79, or text HELP."
OUTSIDE_CA = "That spot is outside California. Text a California orchard as lat,lon, e.g. 39.64,-121.79."
UNAVAILABLE = "Weather data is unavailable right now. Please try again in a minute."
PLACES = {
    "durham": ("Durham", *config.DEMO_PINS["butte-durham"]),
    "butte": ("Durham", *config.DEMO_PINS["butte-durham"]),
    "davis": ("Davis", *config.DEMO_PINS["davis"]),
    "parlier": ("Parlier", *config.DEMO_PINS["parlier"]),
}
# Twilio handles opt-out keywords itself; we just stay quiet.
OPT_OUT = {"stop", "stopall", "unsubscribe", "cancel", "end", "quit"}
LATLON = re.compile(r"^\(?\s*(-?\d+(?:\.\d+)?)\s*[, ]\s*(-?\d+(?:\.\d+)?)\s*\)?$")


@router.post("/sms", summary="Twilio webhook: text a location, get chill and heat back")
async def sms(request: Request) -> Response:
    params = dict(parse_qsl((await request.body()).decode(), keep_blank_values=True))
    if config.TWILIO_AUTH_TOKEN:
        given = request.headers.get("x-twilio-signature", "")
        if not hmac.compare_digest(given, signature(_public_url(request), params, config.TWILIO_AUTH_TOKEN)):
            raise HTTPException(403, "invalid Twilio signature")
    return _twiml(reply_for(params.get("Body", ""), date.today()))


def signature(url: str, params: dict[str, str], token: str) -> str:
    """Twilio's X-Twilio-Signature: base64 HMAC-SHA1 of the URL plus each param name and value, sorted by name."""
    data = url + "".join(k + params[k] for k in sorted(params))
    return base64.b64encode(hmac.new(token.encode(), data.encode(), hashlib.sha1).digest()).decode()


def reply_for(body: str, today: date, render=None) -> str | None:
    text = " ".join(body.split())
    key = text.lower()
    if not text or key in {"help", "info", "?", "hi", "hello", "start"}:
        return HELP
    if key in OPT_OUT:
        return None
    place = parse_place(text)
    if place is None:
        return NOT_UNDERSTOOD
    return reply_for_spot(*place, today, render)


def parse_place(text: str) -> tuple[str | None, float, float] | None:
    """A demo place name or "lat,lon" -> (name, lat, lon); None if it's neither."""
    key = " ".join(text.split()).lower()
    if key in PLACES:
        return PLACES[key]
    m = LATLON.match(" ".join(text.split()))
    return (None, float(m.group(1)), float(m.group(2))) if m else None


def reply_for_spot(name: str | None, lat: float, lon: float, today: date, render=None) -> str:
    """The summary for one spot this season, or a friendly reason there isn't one.

    `render(point_response, name)` writes the summary; the default is the one-text SMS version.
    """
    if not (32.0 <= lat <= 42.1 and -124.5 <= lon <= -114.0):
        return OUTSIDE_CA
    season = today.year if today.month >= 9 else today.year - 1
    try:
        p = point(lat, lon, season, "almond", "09-01", "11-01", "01-01", True)
    except HTTPException:
        return UNAVAILABLE
    return (render or summarize)(p, name)


def summarize(p: dict, name: str | None) -> str:
    """One text, most important first; optional pieces are dropped until it fits in 160 characters."""
    t = p["totals"]
    where = name or f"Orchard near {p['nearest_station']['name']}"
    pieces = [f"{where} {p['season']['label']}: {t['chill_portions']:.0f} chill portions, {t['chill_hours']:.0f} chill hrs"]
    optional = []
    if not p["season"]["complete"] and t["chill_portions"] == 0 and t["chill_hours"] == 0 and p["history"]:
        # Nothing has counted yet this season (e.g. October): last season's total is what's useful.
        last = p["history"][-1]
        optional.append(f". Last season ({last['season']}): {last['totals']['chill_hours']:.0f} chill hrs")
    pct = _vs_normal(p)
    if pct is not None:
        optional.append(f" ({pct:+.0f}% vs normal)")
    if p["forecast"]:
        gain = p["forecast"]["plus14"]["chill_portions"] - t["chill_portions"]
        optional.append(f". Next 14 days: +{gain:.0f} CP")
    err = p["correction"]["expected_error"]
    if err:
        optional.append(f". Accuracy +/-{err['chill_portions']:.1f} CP")
    if p.get("mock"):
        optional.append(". (sample data)")
    for piece in optional:
        if len("".join(pieces) + piece + ".") <= MAX_LEN:
            pieces.append(piece)
    msg = "".join(pieces) + "."
    return msg if len(msg) <= MAX_LEN else msg[: MAX_LEN - 3] + "..."


def _vs_normal(p: dict) -> float | None:
    """Percent vs the 10-season median, for chill portions if there is a median, else chill hours."""
    for metric in ("chill_portions", "chill_hours"):
        pct = vs_normal(p, metric)
        if pct is not None:
            return pct
    return None


def vs_normal(p: dict, metric: str) -> float | None:
    """Percent vs the 10-season median: season totals once a season is over, the same day of season
    while it runs. None when there's nothing to compare yet."""
    in_progress = not p["season"]["complete"]
    day = len(p["daily"]) - 1
    value = p["totals"][metric]
    if in_progress and value == 0:
        return None
    past = sorted(
        h["cumulative"][day][metric] if in_progress and day < len(h["cumulative"]) else h["totals"][metric]
        for h in p["history"]
    )
    if not past:
        return None
    mid = len(past) // 2
    median = past[mid] if len(past) % 2 else (past[mid - 1] + past[mid]) / 2
    return (value - median) / median * 100 if median > 0 else None


def _public_url(request: Request) -> str:
    """The URL Twilio called (and signed), as seen through Vercel's proxy."""
    if config.SMS_WEBHOOK_URL:
        return config.SMS_WEBHOOK_URL
    proto = request.headers.get("x-forwarded-proto", request.url.scheme)
    host = request.headers.get("x-forwarded-host") or request.headers.get("host", request.url.netloc)
    query = f"?{request.url.query}" if request.url.query else ""
    return f"{proto}://{host}{request.url.path}{query}"


def _twiml(message: str | None) -> Response:
    inner = f"<Message>{escape(message)}</Message>" if message else ""
    return Response(f'<?xml version="1.0" encoding="UTF-8"?><Response>{inner}</Response>', media_type="application/xml")
