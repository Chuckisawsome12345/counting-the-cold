import numpy as np

from app.calc.gaps import fill_gaps
import pandas as pd

from app.config import PST
from tests.helpers import hourly


def test_short_gap_interpolated():
    filled, report = fill_gaps(hourly([40, np.nan, np.nan, 46]), max_interp_h=3)
    assert filled.tolist() == [40, 42, 44, 46]
    assert (report.interpolated, report.missing, report.long_gaps) == (2, 0, [])


def test_long_gap_flagged_not_filled():
    filled, report = fill_gaps(hourly([40] + [np.nan] * 5 + [46]), max_interp_h=3)
    assert filled.isna().sum() == 5
    assert report.missing == 5
    assert [g.hours for g in report.long_gaps] == [5]


def test_three_hours_filled_four_not():
    filled, report = fill_gaps(hourly([40, np.nan, np.nan, np.nan, 48, np.nan, np.nan, np.nan, np.nan, 40]))
    assert filled.iloc[:5].tolist() == [40, 42, 44, 46, 48]
    assert filled.iloc[5:9].isna().all()  # a long run is never partly filled
    assert (report.interpolated, report.missing) == (3, 4)
    assert [(g.start, g.end, g.hours) for g in report.long_gaps] == [
        (pd.Timestamp("2025-11-01 05:00", tz=PST), pd.Timestamp("2025-11-01 08:00", tz=PST), 4)
    ]


def test_edges_are_not_extrapolated():
    filled, report = fill_gaps(hourly([np.nan, np.nan, 40, 41, np.nan]))
    assert filled.isna().tolist() == [True, True, False, False, True]
    assert (report.interpolated, report.missing, report.long_gaps) == (0, 3, [])


def test_long_edge_gap_is_reported():
    _, report = fill_gaps(hourly([np.nan] * 6 + [40.0]))
    assert [g.hours for g in report.long_gaps] == [6]


def test_nothing_missing():
    t = hourly([40, 41, 42])
    filled, report = fill_gaps(t)
    assert filled.equals(t) and filled is not t
    assert (report.interpolated, report.missing, report.long_gaps) == (0, 0, [])


def test_max_interp_h_is_configurable():
    filled, report = fill_gaps(hourly([40, np.nan, np.nan, 46]), max_interp_h=1)
    assert filled.isna().sum() == 2 and [g.hours for g in report.long_gaps] == [2]
