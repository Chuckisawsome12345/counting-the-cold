import numpy as np
import pandas as pd
import pytest

from app.calc.projection import analog_percentiles


def curve(daily_gain, days=365):
    return pd.Series(np.cumsum([daily_gain] * days), dtype=float)


def test_adds_each_analog_remaining_gain():
    # Day 100 counted; analogs gained 1, 2, ..., 10 per day, so 265 days remain.
    history = [curve(g) for g in range(1, 11)]
    out = analog_percentiles(50.0, 100, history)
    finals = [50 + 265 * g for g in range(1, 11)]
    assert out == {k: round(float(np.percentile(finals, q)), 1) for k, q in (("p10", 10), ("p50", 50), ("p90", 90))}
    assert out["p10"] < out["p50"] < out["p90"]


def test_day_zero_uses_whole_seasons():
    out = analog_percentiles(0.0, 0, [curve(1.0), curve(1.0)])
    assert out == {"p10": 365.0, "p50": 365.0, "p90": 365.0}


def test_season_over_adds_nothing():
    out = analog_percentiles(70.0, 365, [curve(1.0), curve(2.0)])
    assert out == {"p10": 70.0, "p50": 70.0, "p90": 70.0}


def test_short_analog_season_and_negative_gains():
    leap = curve(1.0, days=366)
    short = curve(1.0, days=365)
    assert analog_percentiles(10.0, 366, [leap, short])["p50"] == 10.0
    falling = pd.Series([5.0, 6.0, 4.0, 3.0])  # Utah can drop in warm spells
    assert analog_percentiles(6.0, 2, [falling])["p50"] == pytest.approx(3.0)


def test_no_history():
    assert analog_percentiles(12.3, 40, []) == {"p10": 12.3, "p50": 12.3, "p90": 12.3}
