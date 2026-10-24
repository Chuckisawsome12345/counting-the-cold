"""Open-Meteo client: hourly 2 m temperature (°F) for any lat/lon. Free, no API key.

Every call goes through sources.cache so the demo doesn't hammer the API.
"""
from datetime import date, timedelta

import httpx
import pandas as pd

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

# The reanalysis archive trails real time by about 5 days; the forecast API covers the gap.
ARCHIVE_LAG_DAYS = 6
TIMEOUT_SECONDS = 30.0

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
    rest from the forecast.
    """
    params = {
        **BASE_PARAMS,
        "latitude": lat,
        "longitude": lon,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "models": model,
    }
    return _hourly_series(_get(ARCHIVE_URL, params, client))


def fetch_forecast_hourly(
    lat: float,
    lon: float,
    past_days: int = 10,
    forecast_days: int = 16,
    client: httpx.Client | None = None,
) -> pd.Series:
    """Forecast temperature_2m in °F, indexed by UTC timestamps, covering recent past + 16 days."""
    params = {
        **BASE_PARAMS,
        "latitude": lat,
        "longitude": lon,
        "past_days": past_days,
        "forecast_days": forecast_days,
    }
    return _hourly_series(_get(FORECAST_URL, params, client))


def _get(url: str, params: dict, client: httpx.Client | None) -> dict:
    owned = client is None
    client = client or httpx.Client(timeout=TIMEOUT_SECONDS)
    try:
        response = client.get(url, params=params)
    except httpx.HTTPError as e:
        raise OpenMeteoError(f"Open-Meteo request failed: {e}") from e
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


def _hourly_series(payload: dict) -> pd.Series:
    if payload.get("hourly_units", {}).get("temperature_2m") != "°F":
        raise OpenMeteoError("expected temperature_2m in °F")
    hourly = payload["hourly"]
    index = pd.DatetimeIndex(pd.to_datetime(hourly["time"]), name="time").tz_localize("UTC")
    # Missing hours come back as null; float dtype turns them into NaN.
    return pd.Series(hourly["temperature_2m"], index=index, dtype=float, name="temp_f")
