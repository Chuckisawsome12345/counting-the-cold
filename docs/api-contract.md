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
    "plus14": {"chill_portions": 3.0, "chill_hours": 30, "utah_units": 39, "gdd": 0}
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

## Stretch endpoints (shapes to be added here before building)

- `GET /api/compare?lat&lon&season`: pin vs nearest station.
- `GET /api/hullsplit?lat&lon&bloom=YYYY-MM-DD&cultivar=`
- `GET /api/v1/models?lat&lon`: public API, totals for every model.

All numbers on this page are illustrative.
