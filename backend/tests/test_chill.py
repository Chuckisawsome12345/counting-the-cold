import numpy as np
import pytest

from app.calc.chill import chill_hours, dynamic_portions, utah_units
from tests.helpers import hourly


def test_chill_hours_bounds_inclusive():
    assert chill_hours(hourly([31, 32, 40, 45, 46])).tolist() == [0, 1, 1, 1, 0]


def test_chill_hours_keeps_missing():
    assert np.isnan(chill_hours(hourly([40, np.nan, 40])).iloc[1])


@pytest.mark.parametrize(
    "temp_f, units",
    [(34, 0), (35, 0.5), (36, 0.5), (37, 1), (48, 1), (49, 0.5), (54, 0.5),
     (55, 0), (60, 0), (61, -0.5), (65, -0.5), (66, -1)],
)
def test_utah_band_edges(temp_f, units):
    assert utah_units(hourly([temp_f])).iloc[0] == units


def test_dynamic_portions_accumulate_and_never_decrease():
    rng = np.random.default_rng(0)
    n = 24 * 60
    temps = 45 + 15 * np.sin(np.arange(n) * 2 * np.pi / 24) + rng.normal(0, 3, n)
    cum = dynamic_portions(hourly(temps))
    assert (cum.diff().dropna() >= 0).all()
    assert cum.iloc[-1] > 0


def test_dynamic_portions_zero_when_hot():
    # At 80°F the intermediate never reaches the threshold, so no portion is banked.
    assert dynamic_portions(hourly([80.0] * 24 * 30)).iloc[-1] == pytest.approx(0, abs=0.01)


def test_dynamic_portions_optimum_is_cool_not_freezing():
    # About 0.8 portions a day at the 6-8 C optimum; much less at freezing; none above ~13 C.
    def month_at(celsius):
        return dynamic_portions(hourly([celsius * 9 / 5 + 32] * 24 * 30)).iloc[-1]

    assert month_at(6) == pytest.approx(24.4, abs=0.2)
    assert month_at(0) < month_at(2) < month_at(6)
    assert month_at(14) == pytest.approx(0, abs=0.01)


def test_dynamic_portions_missing_hours_carry_the_state():
    temps = list(45 + 10 * np.sin(np.arange(24 * 20) * 2 * np.pi / 24))
    full = dynamic_portions(hourly(temps))
    gappy = temps[:100] + [np.nan] * 5 + temps[100:]
    cum = dynamic_portions(hourly(gappy))
    assert not cum.isna().any()
    assert (cum.iloc[100:105] == cum.iloc[99]).all()  # holds through the gap, adds nothing
    assert cum.iloc[-1] == pytest.approx(full.iloc[-1])  # same as running over the valid hours only


def test_dynamic_portions_leading_and_all_missing():
    assert dynamic_portions(hourly([np.nan, np.nan, 42.0, 42.0])).iloc[:2].tolist() == [0.0, 0.0]
    assert dynamic_portions(hourly([np.nan] * 5)).tolist() == [0.0] * 5
    assert dynamic_portions(hourly([])).empty
