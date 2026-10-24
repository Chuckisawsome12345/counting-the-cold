"""Open-Meteo client: hourly 2 m temperature (°F) for any lat/lon. Free, no API key.

Every call goes through sources.cache so the demo doesn't hammer the API.
"""
import time
from datetime import date, timedelta

import httpx
import pandas as pd

from app.sources import cache

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# The reanalysis archive trails real time by about 5 days; the forecast API covers the gap.
ARCHIVE_LAG_DAYS = 6
TIMEOUT_SECONDS = 30.0
# Waits before retrying a 429 (rate or concurrency limit) or 5xx; then give up.
RETRY_DELAYS = (1.0, 2.0, 4.0)
RETRY_STATUSES = {429, 500, 502, 503, 504}

BASE_PARAMS = {"hourly": "temperature_2m", "temperature_unit": "fahrenheit", "timezone": "GMT"}


class OpenMeteoError(RuntimeError):
    pass


def archive_end(today: date) -> date:
    """Last date the archive reliably has; request the rest from the forecast."""
    return today - timedelta(days=ARCHIVE_LAG_DAYS)


def fetch_archive_hourly(
    lat: float,
    lon: float,
    start: date,
    end: date,
    model: str = "best_match",
    client: httpx.Client | None = None,
) -> pd.Series:
    """Reanalysis temperature_2m in °F, indexed by UTC timestamps.

    The archive lags about 5 days, so callers pass end <= archive_end(today) and fill the
    rest from the forecast. Settled ranges are cached forever; a range reaching into the last
    few days is cached for an hour, since the archive is still filling in.
    `series.attrs["stale"]` is True when an expired cached copy was served because Open-Meteo failed.
    """
    params = {
        **BASE_PARAMS,
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "models": model,
    }
    ttl = cache.FOREVER if end <= archive_end(date.today()) else cache.FORECAST_TTL_SECONDS
    return _cached_series(ARCHIVE_URL, params, ttl, client)


def fetch_forecast_hourly(
    lat: float,
    lon: float,
    past_days: int = 10,
    forecast_days: int = 16,
    client: httpx.Client | None = None,
) -> pd.Series:
    """Forecast temperature_2m in °F, indexed by UTC timestamps, covering recent past + 16 days.

    Cached for an hour; `series.attrs["stale"]` as in fetch_archive_hourly.
    """
    params = {
        **BASE_PARAMS,
        "latitude": lat,
        "longitude": lon,
        "past_days": past_days,
        "forecast_days": forecast_days,
    }
    return _cached_series(FORECAST_URL, params, cache.FORECAST_TTL_SECONDS, client)


def _cached_series(url: str, params: dict, ttl: int | None, client: httpx.Client | None) -> pd.Series:
    payload, stale = cache.get_or_fetch(
        cache.cache_key(url, params), lambda: _check_units(_get(url, params, client)), ttl
    )
    series = _hourly_series(payload)
    series.attrs["stale"] = stale
    return series


def _get(url: str, params: dict, client: httpx.Client | None) -> dict:
    owned = client is None
    client = client or httpx.Client(timeout=TIMEOUT_SECONDS)
    try:
        for delay in (*RETRY_DELAYS, None):
            try:
                response = client.get(url, params=params)
            except httpx.HTTPError as e:
                if delay is None:
                    raise OpenMeteoError(f"Open-Meteo request failed: {e}") from e
            else:
                if response.status_code not in RETRY_STATUSES or delay is None:
                    break
            time.sleep(delay)
    finally:
        if owned:
            client.close()
    if response.status_code != 200:
        # Open-Meteo explains bad requests as {"error": true, "reason": "..."}.
        try:
            reason = response.json().get("reason", response.text)
        except ValueError:
            reason = response.text
        raise OpenMeteoError(f"Open-Meteo {response.status_code}: {reason}")
    return response.json()


def _check_units(payload: dict) -> dict:
    # Checked before caching, so a bad payload is never stored.
    if payload.get("hourly_units", {}).get("temperature_2m") != "°F":
        raise OpenMeteoError("expected temperature_2m in °F")
    return payload


def _hourly_series(payload: dict) -> pd.Series:
    hourly = payload["hourly"]
    index = pd.DatetimeIndex(pd.to_datetime(hourly["time"]), name="time").tz_localize("UTC")
    # Missing hours come back as null; float dtype turns them into NaN.
    return pd.Series(hourly["temperature_2m"], index=index, dtype=float, name="temp_f")
