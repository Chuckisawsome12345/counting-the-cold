import pandas as pd

from app.config import PST


def hourly(values, start: str = "2025-11-01") -> pd.Series:
    idx = pd.date_range(start, periods=len(values), freq="h", tz=PST)
    return pd.Series(values, index=idx, dtype=float)


def daily(values, start: str = "2026-03-01") -> pd.Series:
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx, dtype=float)
