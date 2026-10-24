"""Open-Meteo client: hourly 2 m temperature (°F) for any lat/lon. Free, no API key.

Every call goes through sources.cache so the demo doesn't hammer the API.
"""
from datetime import date

import pandas as pd

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


def fetch_archive_hourly(
    lat: float, lon: float, start: date, end: date, model: str = "best_match"
) -> pd.Series:
    """Reanalysis temperature_2m in °F, indexed by UTC timestamps.

    Request with temperature_unit=fahrenheit&timezone=GMT. The archive lags about
    5 days, so callers pass end = today - 6 days and fill the rest from the forecast.
    """
    raise NotImplementedError


def fetch_forecast_hourly(
    lat: float, lon: float, past_days: int = 10, forecast_days: int = 16
) -> pd.Series:
    """Forecast temperature_2m in °F, indexed by UTC timestamps, covering recent past + 16 days."""
    raise NotImplementedError
