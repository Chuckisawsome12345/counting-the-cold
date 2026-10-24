"""Assemble the /api/point response: fetch, normalize, correct, compute, shape."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import pandas as pd

from app.config import PST
from app.pipeline.timeseries import merge_archive_forecast, snap
from app.sources import openmeteo

HISTORY_SEASONS = 10
# Season chunks are fetched in parallel so a brand-new pin loads in seconds, not ~12 s.
# Open-Meteo's free tier answers 429 "Too many concurrent requests" at 6; 3 is safe.
FETCH_WORKERS = 3


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


def build_point(
    lat: float,
    lon: float,
    season: int,
    crop: str,
    portions_start: str,
    hours_start: str,
    gdd_start: str,
    corrected: bool,
) -> dict:
    """Return a dict matching schemas.PointResponse.

    Steps: load_hourly (snap, fetch archive + forecast via cache, merge, PST) -> calc.gaps.fill_gaps
    -> validation.bias correction -> calc models per season -> history, forecast, climatology.
    """
    raise NotImplementedError
