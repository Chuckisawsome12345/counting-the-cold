import numpy as np
import pandas as pd
import pytest

from app.config import PST
from app.pipeline.timeseries import daily_min_max, merge_archive_forecast, snap, to_pst


def utc_series(values, start):
    idx = pd.date_range(start, periods=len(values), freq="h", tz="UTC")
    return pd.Series(values, index=idx, dtype=float)


def test_snap_to_tenth_degree():
    assert snap(39.64, -121.79) == (39.6, -121.8)
    assert snap(38.5357, -121.7764) == (38.5, -121.8)


def test_to_pst_is_fixed_utc_minus_8_all_year():
    winter = to_pst(utc_series([1, 2], "2025-11-01T07:00"))
    assert [t.isoformat() for t in winter.index] == ["2025-10-31T23:00:00-08:00", "2025-11-01T00:00:00-08:00"]
    summer = to_pst(utc_series([1], "2026-07-01T08:00"))  # no daylight saving
    assert summer.index[0].isoformat() == "2026-07-01T00:00:00-08:00"


def test_to_pst_rejects_naive_index():
    with pytest.raises(ValueError):
        to_pst(pd.Series([1.0], index=pd.date_range("2025-11-01", periods=1, freq="h")))


def test_merge_prefers_archive_and_fills_every_hour():
    archive = utc_series([40, 41, np.nan, 43], "2025-11-01T00:00")  # hours 0-3
    forecast = utc_series([90, 91, 92, 93, np.nan], "2025-11-01T02:00")  # hours 2-6, hour 6 missing
    forecast = forecast.drop(forecast.index[3])  # hour 5 absent entirely
    merged = merge_archive_forecast(archive, forecast)

    assert len(merged) == 7  # hours 0-6, complete
    assert merged["temp_f"].tolist()[:5] == [40, 41, 90, 43, 92]
    assert merged["source"].tolist()[:5] == ["archive", "archive", "forecast", "archive", "forecast"]
    assert np.isnan(merged["temp_f"].iloc[5]) and merged["source"].iloc[5] == "forecast"
    assert np.isnan(merged["temp_f"].iloc[6])


def test_merge_with_no_archive_is_all_forecast():
    merged = merge_archive_forecast(utc_series([], "2025-11-01"), utc_series([50, 51], "2025-11-01"))
    assert merged["source"].tolist() == ["forecast", "forecast"]


def test_daily_min_max_uses_pst_days_and_drops_sparse_days():
    idx = pd.date_range("2025-11-01", periods=48, freq="h", tz=PST)
    temps = pd.Series(np.r_[np.arange(30, 54), np.arange(40, 64)], index=idx, dtype=float)
    temps.iloc[24:31] = np.nan  # 7 missing hours on day 2
    daily = daily_min_max(temps)

    assert daily.index.tz is None
    assert [str(d.date()) for d in daily.index] == ["2025-11-01", "2025-11-02"]
    assert (daily.loc["2025-11-01", "tmin"], daily.loc["2025-11-01", "tmax"]) == (30, 53)
    assert daily.loc["2025-11-02", "hours"] == 17
    assert np.isnan(daily.loc["2025-11-02", "tmin"])


def test_daily_min_max_requires_pst():
    with pytest.raises(ValueError):
        daily_min_max(utc_series([1, 2], "2025-11-01"))
