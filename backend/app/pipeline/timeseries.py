"""Turn raw upstream series into one clean hourly PST series."""
import pandas as pd


def snap(lat: float, lon: float, step: float = 0.1) -> tuple[float, float]:
    """Round to the ERA5-Land grid so nearby pins share cache entries."""
    raise NotImplementedError


def to_pst(series_utc: pd.Series) -> pd.Series:
    """Convert a UTC-indexed series to config.PST (fixed UTC-8)."""
    raise NotImplementedError


def merge_archive_forecast(archive: pd.Series, forecast: pd.Series) -> pd.DataFrame:
    """One hourly frame [temp_f, source]; archive wins where both overlap."""
    raise NotImplementedError


def daily_min_max(hourly: pd.Series) -> pd.DataFrame:
    """Daily [tmin, tmax] in °F from an hourly PST series, using PST calendar days."""
    raise NotImplementedError
