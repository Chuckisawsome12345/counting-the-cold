# Deployment and bot setup

## Vercel

Two Vercel projects deploy from `main`:

- **Backend** (`counting-the-cold`, https://counting-the-cold.vercel.app): root directory `backend`, FastAPI preset. The Python function is `api/index.py`, configured in `backend/vercel.json`. Only `main` builds the backend (`git.deploymentEnabled`), which keeps PRs under the free plan's 100 builds a day.
  - Env: `ALLOWED_ORIGINS` = the frontend URL. `CIMIS_KEY` is not needed (only the offline CIMIS scripts use it).
  - The cache lives in `/tmp` and resets on cold starts; committed snapshots cover the demo pins.
- **Frontend** (`counting-the-cold-jfm3`, https://counting-the-cold-jfm3.vercel.app): root directory `frontend`, Vite preset.
  - Env: `VITE_API_URL` = the backend URL, no trailing slash.

Open `/api/health` on the backend a minute before a demo so the first request isn't a cold start.

## Refreshing the data

After changing the models or the validation, rebuild the saved data and commit it:

```bash
cd backend
python scripts/build_validation.py     # data/validation.json and bias_tables.json (CIMIS vs Open-Meteo)
python scripts/prewarm.py --snapshots  # data/snapshots/ for the demo pins
python scripts/build_grid.py --season 2025  # data/grid/2025.json for the statewide chill layer
```

`scripts/fetch_cimis.py` downloads the CIMIS station data into `data/cimis/` and needs `CIMIS_KEY`.

## Telegram bot

`POST /api/telegram` answers a Telegram bot: share a location, type `39.64,-121.79`, or send `/durham`, `/davis` or `/parlier`. `/suggest <place>` adds things to watch for.

1. In Telegram, message **@BotFather**, send `/newbot`, and copy the token.
2. In the Vercel backend project, set `TELEGRAM_BOT_TOKEN` to that token (Production) and redeploy.
3. Open `https://counting-the-cold.vercel.app/api/telegram/setup` once. It should answer `{"ok": true, ...}`.
4. `GET /api/telegram/status` shows Telegram's view of the webhook (last error, pending messages).

The website's chat box uses `GET /api/telegram/preview?text=durham`, which runs the same reply code without Telegram.

## SMS (Twilio)

`POST /api/sms` is a Twilio webhook that replies with a one-text summary (plain ASCII, at most 160 characters). It needs a paid, registered Twilio number, so it isn't live.

1. In Twilio, set the number's "A message comes in" webhook to `https://counting-the-cold.vercel.app/api/sms` (HTTP POST).
2. Set `TWILIO_AUTH_TOKEN` on the backend so only signed Twilio requests are answered, and redeploy.
