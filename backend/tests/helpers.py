import pandas as pd
import pytest

from app.config import PST

# Marks a test whose function is still a stub. Implementing it wrong fails the test;
# implementing it right turns it into XPASS. Remove the marker once it passes.
stub = pytest.mark.xfail(raises=NotImplementedError, reason="stub: remove marker once implemented")


def hourly(values, start: str = "2025-11-01") -> pd.Series:
    idx = pd.date_range(start, periods=len(values), freq="h", tz=PST)
    return pd.Series(values, index=idx, dtype=float)


def daily(values, start: str = "2026-03-01") -> pd.Series:
    idx = pd.date_range(start, periods=len(values), freq="D")
    return pd.Series(values, index=idx, dtype=float)
