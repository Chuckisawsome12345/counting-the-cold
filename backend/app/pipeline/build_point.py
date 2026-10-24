"""Assemble the /api/point response: fetch, normalize, correct, compute, shape.

The math comes from role B's pure functions in app.calc and app.validation. Chill hours, Utah,
GDD and season windows are required (until they exist build_point raises NotImplementedError and
the route serves the mock). The rest degrade until B lands them: the Dynamic Model reads 0, gaps
stay unfilled, the bias correction is skipped (correction.applied = False), and the end-of-season
range is null.
"""
import json
import math
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Callable

import numpy as np
import pandas as pd

from app.calc import chill, gaps, gdd, projection, seasons
from app.calc.crops import CROPS
from app.config import DATA_DIR, PST
from app.pipeline.timeseries import daily_min_max, merge_archive_forecast, snap
from app.sources import openmeteo
from app.validation import bias

HISTORY_SEASONS = 10
# Season chunks are fetched in parallel so a brand-new pin loads in seconds, not ~12 s.
# Open-Meteo's free tier answers 429 "Too many concurrent requests" at 6; 3 is safe.
FETCH_WORKERS = 3
FORECAST_DAYS = 16
# Chill hours and Utah stop counting at the end of February (FNRIC's chill-hours window) and hold
# that value; otherwise summer's negative Utah hours wipe the season total to 0.
CHILL_HOURS_END_MMDD = "03-01"  # exclusive
METRICS = ("chill_portions", "chill_hours", "utah_units", "gdd")
# Written by B's scripts/build_validation.py: {"stations": {"<id>": {"table": [12 rows x 24], "seasons": n}}}
BIAS_TABLES_PATH = DATA_DIR / "bias_tables.json"
VALIDATION_PATH = DATA_DIR / "validation.json"
STATIONS_PATH = DATA_DIR / "stations.json"


def season_bounds(season: int) -> tuple[date, date]:
    """Sep 1 of `season` through Aug 31 of the next year."""
    return date(season, 9, 1), date(season + 1, 8, 31)


def load_hourly(lat: float, lon: float, season: int, today: date, history_seasons: int = HISTORY_SEASONS) -> pd.DataFrame:
    """Hourly PST frame [temp_f, source] for `season` and the `history_seasons` before it.

    Runs from Sep 1 of the oldest season through the end of `season`, or through the last
    forecast hour if the season is still in progress. The archive is fetched one season per
    request, so finished seasons are cached forever and shared between requests; each request
    is padded by a day on both sides because PST trails UTC by 8 hours. The forecast is
    fetched only when the season reaches past what the archive has. Missing hours stay NaN.
    `frame.attrs["stale"]` is True if any part came from an expired cache copy.
    """
    lat, lon = snap(lat, lon)
    last_archive_day = openmeteo.archive_end(today)
    first_day = season_bounds(season - history_seasons)[0]
    last_day = season_bounds(season)[1]

    ranges = []
    for s in range(season - history_seasons, season + 1):
        start, end = season_bounds(s)
        start, end = start - timedelta(days=1), min(end + timedelta(days=1), last_archive_day)
        if start <= end:
            ranges.append((start, end))
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
        chunks = list(pool.map(lambda r: openmeteo.fetch_archive_hourly(lat, lon, *r), ranges))
    archive = _concat(chunks)

    if last_day > last_archive_day:
        forecast = openmeteo.fetch_forecast_hourly(lat, lon)
        chunks.append(forecast)
    else:
        forecast = pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC"))

    merged = merge_archive_forecast(archive, forecast).tz_convert(PST)
    window_start = pd.Timestamp(first_day).tz_localize(PST)
    window_end = pd.Timestamp(last_day + timedelta(days=1)).tz_localize(PST)
    frame = merged[(merged.index >= window_start) & (merged.index < window_end)].copy()
    frame.attrs["stale"] = any(c.attrs.get("stale", False) for c in chunks)
    return frame


def season_slice(frame: pd.DataFrame, season: int) -> pd.DataFrame:
    """The rows of `frame` that fall in `season` (Sep 1 to Aug 31, PST)."""
    start, end = season_bounds(season)
    return frame.loc[pd.Timestamp(start).tz_localize(PST) : pd.Timestamp(end).tz_localize(PST) + pd.Timedelta(hours=23)]


def _concat(chunks: list[pd.Series]) -> pd.Series:
    if not chunks:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([], tz="UTC"))
    s = pd.concat(chunks)
    return s[~s.index.duplicated(keep="first")].sort_index()


@dataclass
class Settings:
    crop: str
    base_f: float
    upper_f: float | None
    portions_start: str
    hours_start: str
    gdd_start: str


def build_point(
    lat: float,
    lon: float,
    season: int,
    crop: str,
    portions_start: str,
    hours_start: str,
    gdd_start: str,
    corrected: bool,
    today: date | None = None,
) -> dict:
    """Return a dict matching schemas.PointResponse.

    Raises NotImplementedError (before any network call) while B's required calc functions are
    stubs, and KeyError for an unknown crop.
    """
    _require_calc()
    today = today or date.today()
    preset = CROPS[crop]
    settings = Settings(crop, preset["base_f"], preset["upper_f"], portions_start, hours_start, gdd_start)

    frame = load_hourly(lat, lon, season, today)
    temps, filled_mask, report = _fill(frame["temp_f"])

    station_list = _stations(lat, lon)
    correction = {"applied": False, "stations": [], "expected_error": None}
    if corrected:
        blended = _blend_bias(station_list)
        if blended is not None:
            table, used = blended
            temps = bias.apply_bias(temps, table)
            correction = {"applied": True, "stations": used, "expected_error": _expected_error(True)}
    if not correction["applied"]:
        correction["expected_error"] = _expected_error(False)

    work = pd.DataFrame({"temp_f": temps, "source": frame["source"], "filled": filled_mask})
    target = _season_daily(work, season, settings)
    history = []
    for s in range(season - HISTORY_SEASONS, season):
        daily = _season_daily(work, s, settings)
        if daily.empty:
            continue
        history.append({
            "season": seasons.season_label(s),
            "totals": _totals(daily.iloc[-1]),
            "cumulative": [{"day": i, **_totals(row)} for i, (_, row) in enumerate(daily.iterrows())],
        })

    observed = target[target.index < pd.Timestamp(today)]
    upcoming = target[target.index >= pd.Timestamp(today)].iloc[:FORECAST_DAYS]
    complete = today > season_bounds(season)[1]
    totals = _totals(observed.iloc[-1]) if len(observed) else dict.fromkeys(METRICS, 0.0)

    forecast = None
    climatology = None
    if not complete and len(upcoming):
        forecast = {
            "daily": [_row(d, r) for d, r in upcoming.iterrows()],
            "plus7": _totals(upcoming.iloc[min(6, len(upcoming) - 1)]),
            "plus14": _totals(upcoming.iloc[min(13, len(upcoming) - 1)]),
        }
        climatology = _climatology(totals, len(observed), history)

    nearest = station_list[0]
    grid_lat, grid_lon = snap(lat, lon)
    return {
        "mock": False,
        "location": {"lat": lat, "lon": lon, "grid_lat": grid_lat, "grid_lon": grid_lon},
        "season": {
            "label": seasons.season_label(season),
            "portions_start": seasons.season_window(season, portions_start)[0].isoformat(),
            "hours_start": seasons.season_window(season, hours_start)[0].isoformat(),
            "gdd_start": seasons.season_window(season, gdd_start)[0].isoformat(),
            "end": season_bounds(season)[1].isoformat(),
            "as_of": today.isoformat(),
            "complete": complete,
        },
        "settings": {"crop": crop, "gdd_base_f": settings.base_f, "gdd_upper_f": settings.upper_f, "corrected": correction["applied"]},
        "totals": totals,
        "daily": [_row(d, r) for d, r in observed.iterrows()],
        "forecast": forecast,
        "history": history,
        "climatology": climatology,
        "quality": _quality(work, report, season, frame.attrs.get("stale", False)),
        "correction": correction,
        "nearest_station": {k: nearest[k] for k in ("id", "name", "active", "distance_km")},
    }


def _require_calc() -> None:
    """Fail fast, before any network call, while B's required functions are stubs."""
    probe = pd.Series([40.0], index=pd.DatetimeIndex([pd.Timestamp("2025-11-01", tz=PST)]))
    seasons.season_label(2025)
    seasons.season_window(2025, "09-01")
    chill.chill_hours(probe)
    chill.utah_units(probe)
    gdd.daily_gdd(pd.Series([60.0]), pd.Series([40.0]), base=50.0)


def _optional(fn: Callable[[], Any], fallback: Any) -> Any:
    try:
        return fn()
    except NotImplementedError:
        return fallback


def _fill(raw: pd.Series) -> tuple[pd.Series, pd.Series, Any]:
    """Gap-fill with B's fill_gaps; until it exists, keep raw values and report no gaps filled."""
    result = _optional(lambda: gaps.fill_gaps(raw), None)
    if result is None:
        return raw, pd.Series(False, index=raw.index), None
    filled, report = result
    return filled, raw.isna() & filled.notna(), report


def _season_daily(work: pd.DataFrame, season: int, settings: Settings) -> pd.DataFrame:
    """Daily rows for one season: tmin/tmax plus each metric's cumulative value at day's end."""
    sl = season_slice(work, season)
    if sl.empty:
        return pd.DataFrame()
    t = sl["temp_f"]
    day_of = sl.index.normalize().tz_localize(None)
    daily = daily_min_max(t)[["tmin", "tmax"]]

    def since(mmdd: str) -> pd.Series:
        start = pd.Timestamp(seasons.season_window(season, mmdd)[0]).tz_localize(PST)
        return t[t.index >= start]

    def end_of_day(cumulative: pd.Series) -> pd.Series:
        if cumulative.empty:
            return pd.Series(0.0, index=daily.index)
        by_day = cumulative.groupby(cumulative.index.normalize().tz_localize(None)).last()
        return by_day.reindex(daily.index).ffill().fillna(0.0)

    portions = _optional(lambda: chill.dynamic_portions(since(settings.portions_start)), pd.Series(dtype=float))
    hours_end = pd.Timestamp(seasons.season_window(season, CHILL_HOURS_END_MMDD)[0]).tz_localize(PST)
    hours_window = since(settings.hours_start)
    hours_window = hours_window[hours_window.index < hours_end]
    chill_cum = chill.chill_hours(hours_window).fillna(0).cumsum()
    utah_cum = _floored_cumsum(chill.utah_units(hours_window).fillna(0))

    gdd_start = pd.Timestamp(seasons.season_window(season, settings.gdd_start)[0])
    per_day = gdd.daily_gdd(daily["tmax"], daily["tmin"], base=settings.base_f, upper=settings.upper_f)
    gdd_cum = per_day.where(daily.index >= gdd_start, 0.0).fillna(0.0).cumsum()

    out = daily.copy()
    out["chill_portions"] = end_of_day(portions.ffill())
    out["chill_hours"] = end_of_day(chill_cum)
    out["utah_units"] = end_of_day(utah_cum)
    out["gdd"] = gdd_cum
    out["source"] = sl["source"].eq("forecast").groupby(day_of).any().map({True: "forecast", False: "archive"})
    out["filled"] = sl["filled"].groupby(day_of).any()
    return out


def _floored_cumsum(x: pd.Series) -> pd.Series:
    """Running total that never drops below 0 (Utah units go negative in warm hours)."""
    total, out = 0.0, np.empty(len(x))
    for i, v in enumerate(x.to_numpy()):
        total = max(0.0, total + v)
        out[i] = total
    return pd.Series(out, index=x.index)


def _totals(row: pd.Series) -> dict:
    return {m: round(float(row[m]), 1) for m in METRICS}


def _row(day: pd.Timestamp, r: pd.Series) -> dict:
    return {
        "date": day.date().isoformat(),
        "tmin": None if pd.isna(r["tmin"]) else round(float(r["tmin"]), 1),
        "tmax": None if pd.isna(r["tmax"]) else round(float(r["tmax"]), 1),
        **_totals(r),
        "source": r["source"],
        "filled": bool(r["filled"]),
    }


def _climatology(totals: dict, day_of_season: int, history: list[dict]) -> dict | None:
    def per_metric(m: str) -> dict:
        curves = [pd.Series([p[m] for p in h["cumulative"]]) for h in history]
        return projection.analog_percentiles(totals[m], day_of_season, curves)

    return _optional(lambda: {m: per_metric(m) for m in METRICS}, None)


def _quality(work: pd.DataFrame, report: Any, season: int, stale: bool) -> dict:
    sl = season_slice(work, season)
    start, end = sl.index.min(), sl.index.max()
    long_gaps = []
    if report is not None:
        for g in report.long_gaps:
            if start <= g.start <= end:
                long_gaps.append({"start": g.start.strftime("%Y-%m-%dT%H:%M"), "end": g.end.strftime("%Y-%m-%dT%H:%M"), "hours": int(g.hours)})
    return {
        "missing_hours": int(sl["temp_f"].isna().sum()),
        "interpolated_hours": int(sl["filled"].sum()),
        "long_gaps": long_gaps,
        "stale": bool(stale),
    }


def _stations(lat: float, lon: float) -> list[dict]:
    """All stations with distance from the pin, nearest first."""
    doc = json.loads(STATIONS_PATH.read_text())
    out = [{**s, "distance_km": round(_km(lat, lon, s["lat"], s["lon"]), 1)} for s in doc["stations"]]
    return sorted(out, key=lambda s: s["distance_km"])


def _km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p = math.pi / 180
    a = math.sin((lat2 - lat1) * p / 2) ** 2 + math.cos(lat1 * p) * math.cos(lat2 * p) * math.sin((lon2 - lon1) * p / 2) ** 2
    return 6371 * 2 * math.asin(math.sqrt(a))


def _blend_bias(station_list: list[dict]) -> tuple[pd.DataFrame, list[dict]] | None:
    """B's blended bias table for the pin, plus the stations used, or None if unavailable."""
    if not BIAS_TABLES_PATH.exists():
        return None
    tables = json.loads(BIAS_TABLES_PATH.read_text())["stations"]
    by_id = {s["id"]: s for s in station_list}
    candidates = [
        bias.BiasCandidate(
            station_id=int(sid),
            table=pd.DataFrame(entry["table"], index=range(1, 13), columns=range(24)),
            distance_km=by_id[int(sid)]["distance_km"],
            active=by_id[int(sid)]["active"],
            seasons=entry["seasons"],
        )
        for sid, entry in tables.items()
        if int(sid) in by_id
    ]
    result = _optional(lambda: bias.blend_tables(candidates), None)
    if result is None:
        return None
    table, weights = result
    used = [
        {"id": c.station_id, "name": by_id[c.station_id]["name"], "active": c.active,
         "distance_km": c.distance_km, "weight": round(float(w), 3)}
        for c, w in sorted(zip(candidates, weights), key=lambda cw: -cw[1])
        if w > 0
    ]
    return table, used


def _expected_error(corrected: bool) -> dict | None:
    """Mean absolute error per metric from B's validation.json, if it has all four."""
    if not VALIDATION_PATH.exists():
        return None
    summary = json.loads(VALIDATION_PATH.read_text()).get("summary", {})
    key = "corrected_mae" if corrected else "raw_mae"
    if not all(m in summary and key in summary[m] for m in METRICS):
        return None
    return {m: round(float(summary[m][key]), 1) for m in METRICS}
