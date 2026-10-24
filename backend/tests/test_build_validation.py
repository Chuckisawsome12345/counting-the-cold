"""scripts/build_validation.py, offline: synthetic CIMIS and gridded series, no network."""
import numpy as np
import pandas as pd
import pytest

from app.config import PST
from app.schemas import ValidationResponse
from scripts import build_validation as bv

SEASON = 2022


def synthetic(offset: float = 0.0, seasons=(SEASON,)) -> pd.Series:
    idx = pd.DatetimeIndex([], tz=PST)
    for s in seasons:
        idx = idx.append(bv.season_hours(s))
    doy = idx.day_of_year.to_numpy()
    temps = 61 + 16 * np.sin(2 * np.pi * (doy - 110) / 365) + 11 * np.sin(2 * np.pi * (idx.hour.to_numpy() - 9) / 24)
    return pd.Series(temps + offset, index=idx)


@pytest.fixture
def offline(monkeypatch):
    """Every station's CIMIS is the same synthetic series; gridded reads 2°F cold everywhere."""
    monkeypatch.setattr(bv, "load_cimis", lambda station, seasons, cimis_dir=None: synthetic())
    monkeypatch.setattr(bv, "fetch_gridded", lambda lat, lon, seasons, model="best_match", pace=0: synthetic(-2.0))


def test_season_totals_has_every_metric():
    totals = bv.season_totals(synthetic(), SEASON)
    assert set(totals) == set(bv.METRICS)
    assert totals["chill_portions"] > 0 and totals["gdd"] > 0


def test_compare_drops_hours_cimis_is_missing():
    truth = synthetic()
    truth.iloc[2000:2300] = np.nan
    entry = bv.compare(truth, synthetic(), synthetic(), SEASON)
    assert entry["raw"] == entry["cimis"] == entry["corrected"]  # same hours, same totals


def test_leave_one_out_never_uses_the_target():
    infos = {6: {"id": 6, "name": "Davis", "lat": 38.54, "lon": -121.78, "active": True},
             12: {"id": 12, "name": "Durham", "lat": 39.61, "lon": -121.82, "active": False},
             244: {"id": 244, "name": "Biggs", "lat": 39.39, "lon": -121.84, "active": True}}
    zero = pd.DataFrame(0.0, index=range(1, 13), columns=range(24))
    tables = {sid: (zero, 5) for sid in infos}
    _, used = bv.leave_one_out(infos[12], tables, infos)
    assert [u["id"] for u in used] == [244, 6]
    assert sum(u["weight"] for u in used) == pytest.approx(1.0, abs=0.002)


def test_correction_recovers_a_uniform_bias(offline):
    validation, tables = bv.build([6, 12, 244], [SEASON], models=False, pace=0)
    ValidationResponse.model_validate(validation)  # the API's contract
    assert {int(k) for k in tables["stations"]} == {6, 12, 244}
    table = np.array(tables["stations"]["12"]["table"])
    assert table.shape == (12, 24) and np.allclose(table, 2.0)
    every = validation["method"]["mae_if_every_metric_corrected"]
    for m in bv.METRICS:
        s = validation["summary"][m]
        assert s["raw_mae"] > 0
        assert every[m]["corrected_mae"] < s["raw_mae"] / 10  # a uniform bias is fully recoverable
        if m in bv.CORRECTED_METRICS:
            assert s["corrected_mae"] < s["raw_mae"] / 10
        else:
            assert s["corrected_mae"] == s["raw_mae"]  # the app leaves chill uncorrected
    durham = next(st for st in validation["stations"] if st["id"] == 12)
    assert [u["id"] for u in durham["corrected_with"]][0] == 244
    assert validation["durham"]["nearest_station_baseline"]["mae"]["chill_portions"] == 0  # identical synthetic data


def test_thin_seasons_are_skipped(monkeypatch):
    thin = synthetic()
    thin.iloc[: len(thin) // 4] = np.nan  # 75% coverage
    monkeypatch.setattr(bv, "load_cimis", lambda station, seasons, cimis_dir=None: thin)
    monkeypatch.setattr(bv, "fetch_gridded", lambda *a, **k: synthetic(-2.0))
    validation, _ = bv.build([6, 244], [SEASON], models=False, pace=0)
    assert validation["stations"] == []
    assert {s["station"] for s in validation["method"]["skipped"]} == {6, 244}


def test_committed_files_match_the_contract():
    path = bv.VALIDATION_PATH
    if not path.exists():
        pytest.skip("validation.json not built yet")
    import json

    v = json.loads(path.read_text())
    ValidationResponse.model_validate(v)
    tables = json.loads(bv.BIAS_TABLES_PATH.read_text())["stations"]
    for entry in tables.values():
        assert np.array(entry["table"]).shape == (12, 24) and entry["seasons"] >= 1
