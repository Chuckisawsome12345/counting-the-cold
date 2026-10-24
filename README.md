# Counting the Cold

**Your orchard's chill and heat, not a station's.**

Drop a pin on any California orchard and see its chill (chill hours, Utah units, Dynamic Model chill portions) and growing degree days for the season so far, compared with the last 10 seasons, plus a 14-day projection. Estimates come from gridded weather data (Open-Meteo), bias-corrected and validated against CIMIS stations, so they work where there is no station, including near the Durham #12 station that closed in July 2025.

Built at Reboot Earth (UC Davis, Oct 23–24 2026) for the FNRIC "Counting the Cold" challenge.

- **Plan:** [`docs/BUILD_PLAN.md`](docs/BUILD_PLAN.md) (change it with a `plan` PR) · **Progress:** [milestones](https://github.com/Chuckisawsome12345/counting-the-cold/milestones)
- **How we work:** [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) · **API shapes:** [`docs/api-contract.md`](docs/api-contract.md)

## Run it locally

```bash
cp .env.example .env
```

Backend (Python 3.12+), on http://localhost:8000 with docs at `/docs`:

```bash
cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload
```

Frontend, on http://localhost:5173 (proxies `/api` to the backend):

```bash
cd frontend && npm install && npm run dev
```

No backend handy? Run the frontend on synthetic data: `VITE_USE_MOCK=1 npm run dev`.

## Checks

```bash
cd backend && pytest
cd frontend && npm run build
```

## Status

Scaffold only. `/api/point` serves synthetic mock data (`"mock": true`) until the real pipeline lands; see the milestones in the plan.

## Data

- [Open-Meteo](https://open-meteo.com) historical archive and forecast (no key).
- [CIMIS](https://cimis.water.ca.gov) station data for validation (key required, offline scripts only).
