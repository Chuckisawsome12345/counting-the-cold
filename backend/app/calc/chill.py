"""Chill models. Pure functions: hourly °F Series (PST index, NaN = missing) in, Series out."""
import numpy as np
import pandas as pd

# Dynamic Model constants (Fishman et al. 1987; chillR::Dynamic_Model).
E0 = 4153.5
E1 = 12888.8
A0 = 139500.0
A1 = 2.567e18
SLP = 1.6
TETMLT = 277.0


def chill_hours(t: pd.Series, lo: float = 32.0, hi: float = 45.0) -> pd.Series:
    """Per hour: 1 if lo <= t <= hi else 0. NaN stays NaN."""
    return ((t >= lo) & (t <= hi)).astype(float).where(t.notna())


def utah_units(t: pd.Series) -> pd.Series:
    """Per hour Utah chill units (Richardson et al. 1974), °F bands:

    <=34: 0 | 35-36: 0.5 | 37-48: 1 | 49-54: 0.5 | 55-60: 0 | 61-65: -0.5 | >65: -1
    The season cumulative is floored at 0 by the caller (build_point does). Bands are defined on
    whole degrees, so fractional readings are split at the half degree (34.4 -> 0, 34.5 -> 0.5).
    NaN stays NaN.
    """
    units = np.select(
        [t < 34.5, t < 36.5, t < 48.5, t < 54.5, t < 60.5, t < 65.5],
        [0.0, 0.5, 1.0, 0.5, 0.0, -0.5],
        default=-1.0,
    )
    return pd.Series(units, index=t.index).where(t.notna())


def dynamic_portions(t: pd.Series) -> pd.Series:
    """Cumulative chill portions (Dynamic Model), same index as t.

    Follow chillR: TK = t_C + 273; xi = sr/(1+sr) with sr = exp(SLP*TETMLT*(TK-TETMLT)/TK);
    xs = (A0/A1)*exp((E1-E0)/TK); ak1 = A1*exp(-E1/TK). The intermediate E evolves hour by hour,
    and once E >= 1 a portion of E*xi is banked. Missing hours carry the state and add nothing.

    Matches chillR::Dynamic_Model step for step: the state starts at E = 0 on the first hour
    (which never banks), and after a banking hour the next step starts from E - E*xi.
    NaN hours are skipped (the model runs over the valid hours as if they were consecutive);
    the cumulative total holds its value through them and is 0 before the first valid hour.
    """
    valid = t.dropna()
    if valid.empty:
        return pd.Series(0.0, index=t.index)
    tk = (valid.to_numpy(dtype=float) - 32.0) * 5.0 / 9.0 + 273.0
    sr = np.exp(SLP * TETMLT * (tk - TETMLT) / tk)
    xi = (sr / (1.0 + sr)).tolist()
    xs = ((A0 / A1) * np.exp((E1 - E0) / tk)).tolist()
    decay = np.exp(-A1 * np.exp(-E1 / tk)).tolist()

    delt = [0.0] * len(tk)
    e_prev = 0.0
    for i in range(1, len(tk)):
        s = e_prev if e_prev < 1.0 else e_prev - e_prev * xi[i - 1]
        e = xs[i] - (xs[i] - s) * decay[i]
        if e >= 1.0:
            delt[i] = e * xi[i]
        e_prev = e

    cumulative = pd.Series(np.cumsum(delt), index=valid.index)
    return cumulative.reindex(t.index).ffill().fillna(0.0)
