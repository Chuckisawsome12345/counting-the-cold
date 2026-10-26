import json
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


# --- full pipeline (build_point.build_point) with synthetic weather ---

from app.calc import chill, gdd, seasons  # noqa: E402
from app.schemas import PointResponse  # noqa: E402


def synthetic_hourly(lat, lon, season, today, history_seasons=build_point.HISTORY_SEASONS):
    """Stands in for build_point.load_hourly: a seasonal + daily temperature cycle, no network."""
    start = pd.Timestamp(f"{season - history_seasons}-09-01", tz=PST)
    end_season = pd.Timestamp(f"{season + 1}-08-31 23:00", tz=PST)
    end = min(end_season, pd.Timestamp(today, tz=PST) + pd.Timedelta(days=16) - pd.Timedelta(hours=1))
    idx = pd.date_range(start, end, freq="h")
    doy = idx.day_of_year.to_numpy()
    temps = 61 + 16 * np.sin(2 * np.pi * (doy - 110) / 365) + 11 * np.sin(2 * np.pi * (idx.hour.to_numpy() - 9) / 24)
    source = np.where(idx < pd.Timestamp(today - timedelta(days=6), tz=PST), "archive", "forecast")
    frame = pd.DataFrame({"temp_f": temps, "source": source}, index=idx)
    frame.attrs["stale"] = False
    return frame


@pytest.fixture
def pipeline(monkeypatch, tmp_path):
    from app.sources import cache

    monkeypatch.setattr(cache, "DB_PATH", tmp_path / "http.sqlite")
    monkeypatch.setattr(build_point, "load_hourly", synthetic_hourly)
    monkeypatch.setattr(build_point, "BIAS_TABLES_PATH", tmp_path / "none.json")
    monkeypatch.setattr(build_point, "VALIDATION_PATH", tmp_path / "none.json")


def run(season, today=date(2026, 10, 23), **kw):
    args = dict(lat=39.64, lon=-121.79, season=season, crop="almond", portions_start="09-01",
                hours_start="11-01", gdd_start="01-01", corrected=True)
    return build_point.build_point(**{**args, **kw}, today=today)


def test_complete_season_matches_contract(pipeline):
    body = PointResponse.model_validate(run(2025)).model_dump()
    assert body["mock"] is False
    assert body["season"]["label"] == "2025-26" and body["season"]["complete"] is True
    assert body["forecast"] is None and body["climatology"] is None
    assert len(body["history"]) == 10 and body["history"][0]["season"] == "2015-16"
    assert len(body["daily"]) == 365
    t = body["totals"]
    assert t["chill_hours"] > 300 and t["gdd"] > 1000 and t["utah_units"] > 0
    assert t["chill_portions"] > 0
    assert body["nearest_station"]["name"] == "Durham"
    assert body["correction"] == {"applied": False, "stations": [], "expected_error": None}
    assert body["quality"]["interpolated_hours"] == 0  # the synthetic weather has no gaps


def test_metrics_respect_start_dates(pipeline):
    daily = {r["date"]: r for r in run(2025)["daily"]}
    assert daily["2025-10-31"]["chill_hours"] == 0 and daily["2025-11-30"]["chill_hours"] > 0
    assert daily["2025-12-31"]["gdd"] == 0 and daily["2026-08-31"]["gdd"] > 0
    hours = [r["chill_hours"] for r in run(2025)["daily"]]
    assert hours == sorted(hours)  # cumulative
    assert daily["2026-02-28"]["utah_units"] == daily["2026-08-31"]["utah_units"] > 0  # held after Feb
    assert daily["2026-02-28"]["chill_hours"] == daily["2026-08-31"]["chill_hours"]


def test_current_season_splits_observed_and_forecast(pipeline):
    body = PointResponse.model_validate(run(2026)).model_dump()
    assert body["season"]["complete"] is False
    assert body["daily"][-1]["date"] == "2026-10-22"
    f = body["forecast"]
    assert len(f["daily"]) == 16 and f["daily"][0]["date"] == "2026-10-23"
    assert f["plus14"]["chill_hours"] >= f["plus7"]["chill_hours"] >= body["totals"]["chill_hours"]
    c = body["climatology"]  # projection landed (#20)
    for m in ("chill_portions", "chill_hours", "utah_units", "gdd"):
        assert c[m]["p10"] <= c[m]["p50"] <= c[m]["p90"]
    assert c["chill_hours"]["p50"] >= body["totals"]["chill_hours"]


def test_dynamic_model_used_once_available(pipeline, monkeypatch):
    monkeypatch.setattr(chill, "dynamic_portions", lambda t: pd.Series(np.arange(len(t)) / 100.0, index=t.index))
    assert run(2025)["totals"]["chill_portions"] > 0


def test_unknown_crop_rejected(pipeline):
    with pytest.raises(KeyError):
        run(2025, crop="kiwi")


def test_floored_cumsum_never_negative():
    out = build_point._floored_cumsum(pd.Series([1.0, -3.0, 2.0, -1.0]))
    assert out.tolist() == [1.0, 0.0, 2.0, 1.0]


# --- statewide grid (scripts/build_grid.py) ---

from scripts import build_grid  # noqa: E402


def test_valley_outline_includes_orchards_not_coast_or_mountains():
    assert build_grid.inside(39.64, -121.79)  # Durham
    assert build_grid.inside(36.74, -119.79)  # Fresno
    assert build_grid.inside(35.37, -119.02)  # Bakersfield
    assert not build_grid.inside(37.77, -122.42)  # San Francisco
    assert not build_grid.inside(39.10, -120.03)  # Lake Tahoe
    assert 80 <= len(build_grid.grid_points()) <= 250


def test_grid_build_collects_totals_per_cell():
    def fake_build(lat, lon, season, *args, history_seasons, **kwargs):
        assert history_seasons == 0
        return {"totals": {"chill_portions": 60.0, "chill_hours": 900.0, "utah_units": 1200.0, "gdd": 2400.0}}

    doc = build_grid.build(2025, step=1.0, pause=0, build=fake_build)
    assert doc["season"] == "2025-26" and doc["cells"]
    assert set(doc["cells"][0]) == {"lat", "lon", "chill_portions", "chill_hours", "utah_units", "gdd"}


def test_correction_moves_heat_not_chill(pipeline, monkeypatch, tmp_path):
    # B's validation: the station correction helps GDD but hurts chill, so it only touches heat.
    tables = tmp_path / "bias_tables.json"
    tables.write_text(json.dumps({"stations": {"12": {"table": [[10.0] * 24] * 12, "seasons": 10}}}))
    monkeypatch.setattr(build_point, "BIAS_TABLES_PATH", tables)
    on, off = run(2025, corrected=True), run(2025, corrected=False)
    assert on["correction"]["applied"] and on["correction"]["stations"][0]["name"] == "Durham"
    assert not off["correction"]["applied"]
    for m in ("chill_portions", "chill_hours", "utah_units"):
        assert on["totals"][m] == off["totals"][m]
    assert on["totals"]["gdd"] > off["totals"]["gdd"]
