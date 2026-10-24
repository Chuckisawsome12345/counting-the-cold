import numpy as np

from app.calc.gaps import fill_gaps
from tests.helpers import hourly, stub


@stub
def test_short_gap_interpolated():
    filled, report = fill_gaps(hourly([40, np.nan, np.nan, 46]), max_interp_h=3)
    assert filled.tolist() == [40, 42, 44, 46]
    assert (report.interpolated, report.missing, report.long_gaps) == (2, 0, [])


@stub
def test_long_gap_flagged_not_filled():
    filled, report = fill_gaps(hourly([40] + [np.nan] * 5 + [46]), max_interp_h=3)
    assert filled.isna().sum() == 5
    assert report.missing == 5
    assert [g.hours for g in report.long_gaps] == [5]
