"""Write synthetic /api/point responses for tests and the frontend's mock mode.

The weather is made up (a Butte County-like seasonal cycle plus noise). Use it for layout and
charts only, never for numbers anyone quotes. Re-run after a contract change:

    python scripts/make_mock.py

Writes backend/tests/fixtures/mock_point.json (2025-26, complete) and mock_point_current.json
(2026-27, with forecast), and copies both to frontend/src/api/mock/ when that folder exists.
"""
import json
import math
import shutil
from datetime import date, timedelta
from pathlib import Path

import numpy as np

BACKEND = Path(__file__).resolve().parents[1]
FRONTEND_MOCK = BACKEND.parent / "frontend" / "src" / "api" / "mock"

PIN = (39.64, -121.79)
AS_OF = date(2026, 10, 23)
BASE_F, UPPER_F = 55.0, 94.0  # almond / navel orangeworm
STATIONS = [  # id, name, active, lat, lon
    (12, "Durham", False, 39.608639, -121.82443),
    (244, "Biggs", True, 39.386632, -121.835278),
    (250, "Williams", True, 39.210667, -122.168889),
]
METRICS = ("chill_portions", "chill_hours", "utah_units", "gdd")


def km(lat1, lon1, lat2, lon2):
    p = math.pi / 180
    a = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def synthetic_days(season, n_days):
    """Daily (tmin, tmax) in °F from Sep 1 of `season`."""
    rng = np.random.default_rng(season)
    start = date(season, 9, 1)
    noise = 0.0
    out = []
    for i in range(n_days):
        d = start + timedelta(days=i)
        phase = 2 * math.pi * (d.timetuple().tm_yday - 110) / 365
        noise = 0.7 * noise + rng.normal(0, 3)
        tmax = 74 + 20 * math.sin(phase) + noise
        tmin = 48 + 12 * math.sin(phase) + 0.6 * noise
        out.append((d, round(tmin, 1), round(tmax, 1)))
    return out


def hourly_from_days(days):
    """24 values per day: cosine rise from tmin at 06:00 to tmax at 15:00, then decay."""
    temps = []
    for _, tmin, tmax in days:
        for h in range(24):
            if 6 <= h <= 15:
                shape = (1 - math.cos(math.pi * (h - 6) / 9)) / 2
            else:
                hh = h - 15 if h > 15 else h + 9
                shape = (1 + math.cos(math.pi * hh / 15)) / 2
            temps.append(tmin + (tmax - tmin) * shape)
    return np.array(temps)


def dynamic_increments(temps_f):
    """Per-hour chill portions, chillR Dynamic_Model algorithm (mock data only)."""
    e0, e1, a0, a1, slp, tetmlt = 4153.5, 12888.8, 139500.0, 2.567e18, 1.6, 277.0
    tk = (temps_f - 32) * 5 / 9 + 273
    sr = np.exp(slp * tetmlt * (tk - tetmlt) / tk)
    xi = sr / (1 + sr)
    xs = (a0 / a1) * np.exp((e1 - e0) / tk)
    ak1 = a1 * np.exp(-e1 / tk)
    e = np.zeros(len(tk))
    for i in range(1, len(tk)):
        s = e[i - 1] if e[i - 1] < 1 else e[i - 1] - e[i - 1] * xi[i - 1]
        e[i] = xs[i] - (xs[i] - s) * np.exp(-ak1[i])
    return np.where(e >= 1, e * xi, 0.0)


def utah(t):
    return np.select(
        [t <= 34, t <= 36, t <= 48, t <= 54, t <= 60, t <= 65], [0, 0.5, 1, 0.5, 0, -0.5], -1
    )


def season_series(season, n_days):
    """Daily rows (date, tmin, tmax, cumulative metrics) for one season."""
    days = synthetic_days(season, n_days)
    temps = hourly_from_days(days)
    portions = dynamic_increments(temps).reshape(-1, 24).sum(axis=1)
    hours = ((temps >= 32) & (temps <= 45)).reshape(-1, 24).sum(axis=1)
    utah_daily = utah(temps).reshape(-1, 24).sum(axis=1)
    # Chill hours and Utah use FNRIC's Nov 1 - end of Feb window.
    hours_start, hours_end = date(season, 11, 1), date(season + 1, 3, 1)
    gdd_start = date(season + 1, 1, 1)
    rows, cp, ch, uu, gd = [], 0.0, 0.0, 0.0, 0.0
    for i, (d, tmin, tmax) in enumerate(days):
        cp += portions[i]
        if hours_start <= d < hours_end:
            ch += hours[i]
            uu = max(0.0, uu + utah_daily[i])
        if d >= gdd_start:
            gd += max(0.0, (min(tmax, UPPER_F) + tmin) / 2 - BASE_F)
        rows.append({"date": d.isoformat(), "tmin": tmin, "tmax": tmax,
                     "chill_portions": round(cp, 1), "chill_hours": float(ch),
                     "utah_units": round(uu, 1), "gdd": round(gd, 1)})
    return rows


def season_days(season):
    return (date(season + 1, 8, 31) - date(season, 9, 1)).days + 1


def totals(row):
    return {m: row[m] for m in METRICS}


def history(season):
    out = []
    for s in range(season - 10, season):
        rows = season_series(s, season_days(s))
        out.append({
            "season": f"{s}-{str(s + 1)[2:]}",
            "totals": totals(rows[-1]),
            "cumulative": [{"day": i, **totals(r)} for i, r in enumerate(rows)],
        })
    return out


def build(season):
    complete = season < 2026
    label = f"{season}-{str(season + 1)[2:]}"
    hist = history(season)
    dists = [(sid, name, active, km(*PIN, lat, lon)) for sid, name, active, lat, lon in STATIONS]
    inv = [1 / d**2 for *_, d in dists]
    if complete:
        rows = season_series(season, season_days(season))
        daily, forecast, clim = rows, None, None
    else:
        n_obs = (AS_OF - date(season, 9, 1)).days
        rows = season_series(season, n_obs + 16)
        daily, fc = rows[:n_obs], rows[n_obs:]
        forecast = {
            "daily": [{**r, "source": "forecast", "filled": False} for r in fc],
            "plus7": totals(fc[6]),
            "plus14": totals(fc[13]),
        }
        now = daily[-1]
        clim = {}
        for m in METRICS:
            ends = [now[m] + h["cumulative"][-1][m] - h["cumulative"][n_obs - 1][m] for h in hist]
            p10, p50, p90 = np.percentile(ends, [10, 50, 90])
            clim[m] = {"p10": round(p10, 1), "p50": round(p50, 1), "p90": round(p90, 1)}
    return {
        "mock": True,
        "location": {"lat": PIN[0], "lon": PIN[1], "grid_lat": 39.6, "grid_lon": -121.8},
        "season": {
            "label": label,
            "portions_start": f"{season}-09-01",
            "hours_start": f"{season}-11-01",
            "gdd_start": f"{season + 1}-01-01",
            "end": f"{season + 1}-08-31",
            "as_of": AS_OF.isoformat(),
            "complete": complete,
        },
        "settings": {"crop": "almond", "gdd_base_f": BASE_F, "gdd_upper_f": UPPER_F, "corrected": True},
        "totals": totals(daily[-1]),
        "daily": [{**r, "source": "archive", "filled": r["date"] == f"{season}-12-14"} for r in daily],
        "forecast": forecast,
        "history": hist,
        "climatology": clim,
        "quality": {
            "missing_hours": 6,
            "interpolated_hours": 3,
            "long_gaps": [{"start": f"{season + 1}-01-17T02:00", "end": f"{season + 1}-01-17T07:00", "hours": 6}] if complete else [],
            "stale": False,
        },
        "correction": {
            "applied": True,
            "stations": [
                {"id": sid, "name": name, "active": active, "distance_km": round(d, 1), "weight": round(w / sum(inv), 3)}
                for (sid, name, active, d), w in zip(dists, inv)
            ],
            "expected_error": {"chill_portions": 2.1, "chill_hours": 48, "utah_units": 61, "gdd": 54},
        },
        "nearest_station": {"id": dists[0][0], "name": dists[0][1], "active": dists[0][2], "distance_km": round(dists[0][3], 1)},
    }


def main():
    for season, name in ((2025, "mock_point.json"), (2026, "mock_point_current.json")):
        path = BACKEND / "tests" / "fixtures" / name
        path.write_text(json.dumps(build(season), separators=(",", ":")) + "\n")
        print("wrote", path)
        if FRONTEND_MOCK.is_dir():
            dest = FRONTEND_MOCK / name.replace("mock_", "")
            shutil.copyfile(path, dest)
            print("wrote", dest)


if __name__ == "__main__":
    main()
