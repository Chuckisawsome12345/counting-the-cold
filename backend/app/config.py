"""Runtime settings, read from environment variables (and the repo-root .env in local dev)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
DATA_DIR = BACKEND_DIR / "data"

load_dotenv(REPO_ROOT / ".env")

# On Vercel only /tmp is writable, and it's per instance, so the cache lasts until a cold start.
# Committed snapshots cover the demo pins either way.
CACHE_DIR = Path(os.getenv("CACHE_DIR") or ("/tmp/counting-the-cold-cache" if os.getenv("VERCEL") else BACKEND_DIR / ".cache"))

CIMIS_KEY = os.getenv("CIMIS_KEY", "")
# Text-message access (/api/sms): Twilio's auth token turns on signature checks; the webhook URL
# overrides the URL used for them if the proxy hides the one Twilio called.
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
SMS_WEBHOOK_URL = os.getenv("SMS_WEBHOOK_URL", "")
# Telegram bot (/api/telegram): token from @BotFather; the webhook URL overrides the one setup registers.
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_WEBHOOK_URL = os.getenv("TELEGRAM_WEBHOOK_URL", "")
# Where bot replies send people for charts.
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://countingthecold.vercel.app")
DEMO_MODE = os.getenv("DEMO_MODE", "0") == "1"
# The site's own production addresses are always allowed, so renaming its domain can't silently
# block every API call; ALLOWED_ORIGINS adds to them (local dev, previews).
SITE_ORIGINS = ["https://countingthecold.vercel.app", "https://counting-the-cold-jfm3.vercel.app"]
ALLOWED_ORIGINS = list(dict.fromkeys([
    *(o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",") if o.strip()),
    *SITE_ORIGINS,
]))

# Fixed UTC-8 with no daylight saving, to match CIMIS. Note the inverted sign in the Etc/ zone name.
PST = "Etc/GMT+8"

# Pins the demo uses; scripts/prewarm.py caches and snapshots these.
DEMO_PINS = {
    "butte-durham": (39.640, -121.790),  # orchard near the closed Durham #12 station
    "davis": (38.5357, -121.7764),
    "parlier": (36.5974, -119.5040),
}
