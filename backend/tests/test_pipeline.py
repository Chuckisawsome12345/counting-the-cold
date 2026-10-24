from datetime import date, timedelta

import numpy as np
import pandas as pd
import pytest

from app.config import PST
from app.pipeline import build_point
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


# --- season data loader (build_point.load_hourly) ---



class FakeOpenMeteo:
    """Stands in for app.sources.openmeteo: synthetic hourly data for whatever range is asked."""

    def __init__(self, stale=False):
        self.archive_calls = []
        self.forecast_calls = 0
        self.stale = stale

    def archive_end(self, today):
        return today - timedelta(days=6)

    def fetch_archive_hourly(self, lat, lon, start, end):
        self.archive_calls.append((lat, lon, start, end))
        idx = pd.date_range(pd.Timestamp(start, tz="UTC"), pd.Timestamp(end, tz="UTC") + pd.Timedelta(hours=23), freq="h")
        s = pd.Series(50.0, index=idx)
        s.attrs["stale"] = self.stale
        return s

    def fetch_forecast_hourly(self, lat, lon):
        self.forecast_calls += 1
        today = pd.Timestamp("2026-10-23", tz="UTC")
        idx = pd.date_range(today - pd.Timedelta(days=10), today + pd.Timedelta(days=16) - pd.Timedelta(hours=1), freq="h")
        return pd.Series(60.0, index=idx)


@pytest.fixture
def fake_om(monkeypatch):
    fake = FakeOpenMeteo()
    monkeypatch.setattr(build_point, "openmeteo", fake)
    return fake


def test_complete_season_loads_eleven_padded_chunks_and_no_forecast(fake_om):
    frame = build_point.load_hourly(39.64, -121.79, 2024, today=date(2026, 10, 23))
    assert len(fake_om.archive_calls) == 11
    assert fake_om.forecast_calls == 0
    lat, lon, start, end = fake_om.archive_calls[0]
    assert (lat, lon) == (39.6, -121.8)  # snapped
    assert (start, end) == (date(2014, 8, 31), date(2015, 9, 1))  # one day of padding each side
    assert str(frame.index.tz) == PST
    assert frame.index[0] == pd.Timestamp("2014-09-01", tz=PST)
    assert frame.index[-1] == pd.Timestamp("2025-08-31 23:00", tz=PST)
    assert frame.index.is_unique and len(frame) == pd.date_range(frame.index[0], frame.index[-1], freq="h").size
    assert set(frame["source"]) == {"archive"}


def test_current_season_adds_forecast_and_stops_at_its_end(fake_om):
    frame = build_point.load_hourly(39.64, -121.79, 2026, today=date(2026, 10, 23))
    assert fake_om.forecast_calls == 1
    current_chunk = max(fake_om.archive_calls, key=lambda call: call[2])  # calls run in parallel, any order
    assert current_chunk[3] == date(2026, 10, 17)  # ends at archive_end
    assert frame.index[-1] < pd.Timestamp("2026-11-08", tz=PST)
    current = build_point.season_slice(frame, 2026)
    assert current["source"].iloc[-1] == "forecast"
    assert current.index[0] == pd.Timestamp("2026-09-01", tz=PST)


def test_stale_flag_propagates(monkeypatch):
    fake = FakeOpenMeteo(stale=True)
    monkeypatch.setattr(build_point, "openmeteo", fake)
    assert build_point.load_hourly(39.64, -121.79, 2024, today=date(2026, 10, 23)).attrs["stale"] is True


def test_season_slice_is_sep_1_to_aug_31(fake_om):
    frame = build_point.load_hourly(39.64, -121.79, 2024, today=date(2026, 10, 23))
    s = build_point.season_slice(frame, 2020)
    assert (s.index[0], s.index[-1]) == (pd.Timestamp("2020-09-01", tz=PST), pd.Timestamp("2021-08-31 23:00", tz=PST))
    assert len(s) == 365 * 24
