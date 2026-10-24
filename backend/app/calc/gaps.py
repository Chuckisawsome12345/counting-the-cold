"""Missing-hour handling. Interpolate short gaps, flag long ones for the UI."""
from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class LongGap:
    start: pd.Timestamp
    end: pd.Timestamp
    hours: int


@dataclass
class GapReport:
    missing: int = 0  # hours still NaN after filling
    interpolated: int = 0  # hours filled by interpolation
    long_gaps: list[LongGap] = field(default_factory=list)


def fill_gaps(t: pd.Series, max_interp_h: int = 3) -> tuple[pd.Series, GapReport]:
    """Linearly interpolate runs of NaN up to max_interp_h hours; leave longer runs NaN and report them.

    t must already be on a complete hourly index (the caller reindexes), so missing hours are NaN.
    Only runs with a reading on both sides are interpolated; a run at the very start or end stays
    NaN (and is a long gap if it's longer than max_interp_h). Long runs are never partly filled.
    """
    isna = t.isna().to_numpy()
    if not isna.any():
        return t.copy(), GapReport()
    n = len(isna)
    edges = np.diff(np.concatenate(([0], isna.astype(np.int8), [0])))
    starts = np.flatnonzero(edges == 1)
    ends = np.flatnonzero(edges == -1)  # exclusive
    lengths = ends - starts

    short = (starts > 0) & (ends < n) & (lengths <= max_interp_h)
    fill = np.zeros(n, dtype=bool)
    for s, e in zip(starts[short], ends[short]):
        fill[s:e] = True
    interpolated = t.interpolate(method="linear", limit_area="inside")
    filled = t.where(~fill, interpolated)

    long_gaps = [
        LongGap(start=t.index[s], end=t.index[e - 1], hours=int(e - s))
        for s, e in zip(starts, ends)
        if e - s > max_interp_h
    ]
    report = GapReport(missing=int(filled.isna().sum()), interpolated=int(fill.sum()), long_gaps=long_gaps)
    return filled, report
