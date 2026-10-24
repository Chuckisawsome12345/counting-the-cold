import pytest

from app.calc.gdd import daily_gdd
from tests.helpers import daily


def test_average_method():
    assert daily_gdd(daily([80]), daily([50]), base=50).iloc[0] == 15


def test_below_base_is_zero():
    assert daily_gdd(daily([48]), daily([30]), base=50).iloc[0] == 0


def test_upper_horizontal_cutoff():
    out = daily_gdd(daily([100]), daily([60]), base=55, upper=94)
    assert out.iloc[0] == pytest.approx((94 + 60) / 2 - 55)
