"""Missing-hour handling. Interpolate short gaps, flag long ones for the UI."""
from dataclasses import dataclass, field

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
    """
    raise NotImplementedError
