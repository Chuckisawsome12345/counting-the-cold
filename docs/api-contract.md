# API contract

Source of truth for every JSON shape. Mirrored in `backend/app/schemas.py` (pydantic) and `frontend/src/api/types.ts`. Change it only through a `contract` PR (see `CONTRIBUTING.md`).

Conventions:

- Temperatures in °F, degree days in °F-days. Dates are ISO `YYYY-MM-DD`; timestamps are PST (UTC−8, no daylight saving).
- A season runs Sep 1 to Aug 31. `season=2025` means Sep 1 2025 to Aug 31 2026, labeled `"2025-26"`.
- Metric values in `daily` and `history[].cumulative` are **cumulative season-to-date**, and 0 before that metric's start date.
- Default windows: portions from Sep 1; chill hours and Utah from Nov 1 (FNRIC stops chill hours at the end of February; B decides whether to cap); GDD from Jan 1.
- The four metric keys everywhere: `chill_portions`, `chill_hours`, `utah_units`, `gdd`.

## GET /api/health

```json
{"ok": true, "demo_mode": false, "cache_entries": 0}
```

## GET /api/point

| Param | Default | Notes |
|---|---|---|
| `lat`, `lon` | required | California only: lat 32–42.1, lon −124.5 to −114, else 422 |
| `season` | `2025` | Season start year |
| `crop` | `almond` | Preset id from `/api/crops` |
| `portions_start`, `hours_start`, `gdd_start` | `09-01`, `11-01`, `01-01` | `MM-DD` |
| `corrected` | `true` | Apply the station bias correction |

```jsonc
{
  "mock": false,                       // true for synthetic responses from scripts/make_mock.py
  "location": {"lat": 39.64, "lon": -121.79, "grid_lat": 39.6, "grid_lon": -121.8},
  "season": {
    "label": "2025-26",
    "portions_start": "2025-09-01", "hours_start": "2025-11-01", "gdd_start": "2026-01-01",
    "end": "2026-08-31",
    "as_of": "2026-10-23",
    "complete": true                   // false for the season in progress
  },
  "settings": {"crop": "almond", "gdd_base_f": 55, "gdd_upper_f": 94, "corrected": true},
  "totals": {"chill_portions": 62.1, "chill_hours": 1012, "utah_units": 1304, "gdd": 2450},
  "daily": [
    {"date": "2025-09-01", "tmin": 55.2, "tmax": 91.0,
     "chill_portions": 0, "chill_hours": 0, "utah_units": 0, "gdd": 0,
     "source": "archive",              // "archive" | "forecast"
     "filled": false}                  // true if any hour that day was interpolated
  ],
  "forecast": {                        // null when season.complete
    "daily": [/* 16 rows, same shape as daily, source "forecast" */],
    "plus7":  {"chill_portions": 1.2, "chill_hours": 0, "utah_units": 0, "gdd": 0},
    "plus14": {"chill_portions": 3.0, "chill_hours": 30, "utah_units": 39, "gdd": 0}   // running totals (season-to-date) at +7 and +14 days, not gains; gain = plus14 - totals
  },
  "history": [                         // the 10 seasons before this one, oldest first
    {"season": "2015-16",
     "totals": {"chill_portions": 70.4, "chill_hours": 1100, "utah_units": 1400, "gdd": 2380},
     "cumulative": [{"day": 0, "chill_portions": 0, "chill_hours": 0, "utah_units": 0, "gdd": 0}]}
  ],
  "climatology": {                     // end-of-season range; null when season.complete
    "chill_portions": {"p10": 55, "p50": 63, "p90": 70},
    "chill_hours": {"p10": 0, "p50": 0, "p90": 0},
    "utah_units": {"p10": 0, "p50": 0, "p90": 0},
    "gdd": {"p10": 0, "p50": 0, "p90": 0}
  },
  "quality": {
    "missing_hours": 6, "interpolated_hours": 3,
    "long_gaps": [{"start": "2026-01-17T02:00", "end": "2026-01-17T07:00", "hours": 6}],
    "stale": false                     // true when served from an expired cache entry
  },
  "correction": {
    "applied": true,
    "stations": [{"id": 12, "name": "Durham", "active": false, "distance_km": 4.6, "weight": 0.97}],
    "expected_error": {"chill_portions": 2.1, "chill_hours": 48, "utah_units": 61, "gdd": 54}  // or null
  },
  "nearest_station": {"id": 12, "name": "Durham", "active": false, "distance_km": 4.6}
}
```

`day` in `history[].cumulative` counts days since Sep 1 of that season (0-based).

## GET /api/stations

```json
{"stations": [
  {"id": 12, "name": "Durham", "city": "Durham", "county": "Butte",
   "lat": 39.608639, "lon": -121.82443, "elevation_ft": 130,
   "active": false, "connect_date": "1982-10-19", "disconnect_date": "2025-07-30",
   "group": "durham",
   "validation": {"chill_portions": {"raw_mae": 4.2, "corrected_mae": 1.9}}}
]}
```

`group` is `core`, `durham`, or `durham-neighbor`. `validation` is null until `validation.json` exists.

## GET /api/validation

```json
{
  "built_at": "2026-10-24T03:00:00",
  "summary": {"chill_portions": {"raw_mae": 4.2, "corrected_mae": 1.9}},
  "stations": [
    {"id": 12, "name": "Durham",
     "mae": {"chill_portions": {"raw_mae": 4.2, "corrected_mae": 1.9}},
     "seasons": [
       {"season": "2024-25",
        "cimis":     {"chill_portions": 64.0, "chill_hours": 1010, "utah_units": 1290, "gdd": 2400},
        "raw":       {"chill_portions": 59.1, "chill_hours": 950,  "utah_units": 1210, "gdd": 2460},
        "corrected": {"chill_portions": 62.8, "chill_hours": 995,  "utah_units": 1275, "gdd": 2415}}
     ]}
  ]
}
```

Before `build_validation.py` has run: `{"built_at": null, "summary": {}, "stations": []}`.

## GET /api/crops

```json
{"crops": [{"id": "almond", "label": "Almond (navel orangeworm)", "base_f": 55, "upper_f": 94}]}
```

## GET /api/v1/models

Public, embeddable summary for one location: our adoption path (FNRIC or extension advisors can show "estimate for your exact orchard"). Uses the default windows and the bias correction.

| Param | Default | Notes |
|---|---|---|
| `lat`, `lon` | required | California only |
| `season` | `2025` | Season start year |
| `crop` | `almond` | GDD preset from `/api/crops` |

```jsonc
{
  "mock": false,
  "location": {"lat": 39.64, "lon": -121.79, "grid_lat": 39.6, "grid_lon": -121.8},
  "season": "2025-26", "as_of": "2026-10-23", "complete": true, "corrected": true,
  "models": {
    "chill_portions": {"value": 62.1, "unit": "CP", "window_start": "2025-09-01", "model": "Dynamic Model (Fishman et al. 1987), FNRIC's preferred chill model"},
    "chill_hours":    {"value": 1012, "unit": "h",  "window_start": "2025-11-01", "model": "Hours between 32 and 45 °F, through end of February"},
    "utah_units":     {"value": 1304, "unit": "CU", "window_start": "2025-11-01", "model": "Utah Model (Richardson et al. 1974), running total floored at 0"},
    "gdd":            {"value": 2450, "unit": "°F-days", "window_start": "2026-01-01", "model": "Average method, base 55 °F, upper 94 °F (almond preset, UC IPM thresholds)"}
  },
  "expected_error": {"chill_portions": 2.1, "chill_hours": 48, "utah_units": 61, "gdd": 54},  // or null
  "nearest_station": {"id": 12, "name": "Durham", "active": false, "distance_km": 4.6},
  "attribution": "Counting the Cold: Open-Meteo hourly temperatures, bias-corrected against CIMIS stations. ..."
}
```

## GET /api/grid

One metric on the precomputed Central Valley grid (about 0.25°), for the statewide map layer. Built offline by `backend/scripts/build_grid.py` into `backend/data/grid/<season>.json`.

| Param | Default | Notes |
|---|---|---|
| `season` | `2025` | Season start year |
| `metric` | `chill_portions` | One of the four metric keys |

```json
{"season": "2025-26", "metric": "chill_portions", "unit": "CP", "step_deg": 0.25,
 "built_at": "2026-10-24T02:00:00+00:00",
 "cells": [{"lat": 39.5, "lon": -121.75, "value": 61.8}]}
```

Each cell's `lat`/`lon` is the cell **centre**; the cell spans ±`step_deg`/2 around it.

Before the grid is built: `"built_at": null, "cells": []`.

## GET /api/telegram/preview

The Telegram bot's reply to one message, computed by the same code the bot uses, so the website can show the bot without Telegram (a "Try the bot" box). Plain text with line breaks (render with `white-space: pre-wrap`).

| Param | Default | Notes |
|---|---|---|
| `text` | `""` | What the user would send: `durham`, `davis`, `parlier`, `39.64,-121.79`, `/suggest durham`, `/help`. At most 200 characters. Empty gives the help text. |

```json
{"text": "Durham · 2026-27 season (as of Oct 24)\n\nChill (winter cold)\n• Chill portions: 3 so far (since Sep 1; ▼12% vs the 10-season median)\n...",
 "bot_url": "https://t.me/ExampleBot"}
```

`bot_url` opens the real bot in Telegram; `null` when the bot isn't configured or Telegram can't be reached.

All numbers on this page are illustrative.
