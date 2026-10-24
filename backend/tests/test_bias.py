import numpy as np
import pandas as pd

from app.config import PST
import pytest

from app.validation.bias import BiasCandidate, apply_bias, blend_tables, fit_bias_table
from app.validation.metrics import bias, mae


def test_constant_offset_recovered_and_applied():
    idx = pd.date_range("2024-01-01", "2024-12-31 23:00", freq="h", tz=PST)
    rng = np.random.default_rng(1)
    observed = pd.Series(
        50 + 15 * np.sin(np.arange(len(idx)) * 2 * np.pi / 24) + rng.normal(0, 2, len(idx)), index=idx
    )
    gridded = observed - 2.0
    table = fit_bias_table(gridded, observed)
    assert table.shape == (12, 24)
    assert np.allclose(table.values, 2.0)
    assert np.allclose(apply_bias(gridded, table).values, observed.values)


def const_table(v):
    return pd.DataFrame(float(v), index=range(1, 13), columns=range(24))


def cand(sid, v, km, active=True, seasons=10):
    return BiasCandidate(station_id=sid, table=const_table(v), distance_km=km, active=active, seasons=seasons)


def test_table_is_by_month_and_hour():
    idx = pd.date_range("2024-01-01", "2024-12-31 23:00", freq="h", tz=PST)
    observed = pd.Series(50.0, index=idx)
    gridded = observed - np.where(idx.month == 7, 3.0, 0.0) - np.where(idx.hour == 5, 1.0, 0.0)
    table = fit_bias_table(gridded, observed)
    assert list(table.index) == list(range(1, 13)) and list(table.columns) == list(range(24))
    assert table.loc[7, 12] == pytest.approx(3.0) and table.loc[1, 5] == pytest.approx(1.0)
    assert table.loc[7, 5] == pytest.approx(4.0) and table.loc[2, 0] == pytest.approx(0.0)


def test_missing_cells_take_the_hour_mean():
    idx = pd.date_range("2024-01-01", "2024-02-29 23:00", freq="h", tz=PST)  # Jan and Feb only
    observed = pd.Series(50.0, index=idx)
    gridded = observed - np.where(idx.month == 1, 2.0, 4.0)
    table = fit_bias_table(gridded, observed)
    assert not table.isna().any().any()
    assert table.loc[6, 10] == pytest.approx(3.0)


def test_apply_keeps_missing():
    t = pd.Series([50.0, np.nan], index=pd.date_range("2024-07-01", periods=2, freq="h", tz=PST))
    out = apply_bias(t, const_table(1.5))
    assert out.iloc[0] == 51.5 and np.isnan(out.iloc[1])


def test_inverse_distance_weights():
    table, weights = blend_tables([cand(1, 1.0, 10), cand(2, 4.0, 20), cand(3, 9.0, 200)])
    assert weights == pytest.approx([0.8, 0.2, 0.0])  # 1/100 : 1/400, the 200 km one is out
    assert np.allclose(table.values, 0.8 * 1.0 + 0.2 * 4.0)


def test_closed_station_nearby_anchors_the_pin():
    # Durham-like: closed, 8 km, 10 seasons. IDW alone would give it ~66%; the rule lifts it to 90%.
    _, weights = blend_tables([cand(12, 1.0, 8, active=False), cand(244, 3.0, 12), cand(250, 5.0, 40)])
    assert weights[0] == pytest.approx(0.9)
    assert sum(weights) == pytest.approx(1.0)
    assert weights[1] > weights[2] > 0


def test_closed_station_rule_needs_history_and_proximity():
    _, few = blend_tables([cand(12, 1.0, 8, active=False, seasons=2), cand(244, 3.0, 12)])
    _, far = blend_tables([cand(12, 1.0, 15, active=False), cand(244, 3.0, 12)])
    assert few[0] < 0.9 and far[0] < 0.9


def test_already_dominant_closed_station_keeps_its_idw_weight():
    _, weights = blend_tables([cand(12, 1.0, 2, active=False), cand(244, 3.0, 25)])
    assert weights[0] > 0.99


def test_only_station_and_none_in_range():
    table, weights = blend_tables([cand(12, 2.0, 5, active=False)])
    assert weights == [1.0] and np.allclose(table.values, 2.0)
    assert blend_tables([cand(1, 1.0, 300)]) is None
    assert blend_tables([]) is None


def test_pin_on_a_station():
    _, weights = blend_tables([cand(1, 1.0, 0.0), cand(2, 4.0, 30)])
    assert weights[0] > 0.99


def test_mae_and_bias():
    assert mae([1, 2, 3], [1, 4, 0]) == pytest.approx(5 / 3)
    assert mae([1, np.nan], [2, 5]) == 1.0
    assert np.isnan(mae([np.nan], [1]))
    assert bias([3, 5], [1, 2]) == 2.5
    with pytest.raises(ValueError):
        mae([1, 2], [1])
