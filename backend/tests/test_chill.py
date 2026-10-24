import numpy as np
import pytest

from app.calc.chill import chill_hours, dynamic_portions, utah_units
from tests.helpers import hourly, stub


@stub
def test_chill_hours_bounds_inclusive():
    assert chill_hours(hourly([31, 32, 40, 45, 46])).tolist() == [0, 1, 1, 1, 0]


@stub
def test_chill_hours_keeps_missing():
    assert np.isnan(chill_hours(hourly([40, np.nan, 40])).iloc[1])


@stub
@pytest.mark.parametrize(
    "temp_f, units",
    [(34, 0), (35, 0.5), (36, 0.5), (37, 1), (48, 1), (49, 0.5), (54, 0.5),
     (55, 0), (60, 0), (61, -0.5), (65, -0.5), (66, -1)],
)
def test_utah_band_edges(temp_f, units):
    assert utah_units(hourly([temp_f])).iloc[0] == units


@stub
def test_dynamic_portions_accumulate_and_never_decrease():
    rng = np.random.default_rng(0)
    n = 24 * 60
    temps = 45 + 15 * np.sin(np.arange(n) * 2 * np.pi / 24) + rng.normal(0, 3, n)
    cum = dynamic_portions(hourly(temps))
    assert (cum.diff().dropna() >= 0).all()
    assert cum.iloc[-1] > 0


@stub
def test_dynamic_portions_zero_when_hot():
    # At 80°F the intermediate never reaches the threshold, so no portion is banked.
    assert dynamic_portions(hourly([80.0] * 24 * 30)).iloc[-1] == pytest.approx(0, abs=0.01)
