"""Chill models. Pure functions: hourly °F Series (PST index, NaN = missing) in, Series out."""
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
    raise NotImplementedError


def utah_units(t: pd.Series) -> pd.Series:
    """Per hour Utah chill units (Richardson et al. 1974), °F bands:

    <=34: 0 | 35-36: 0.5 | 37-48: 1 | 49-54: 0.5 | 55-60: 0 | 61-65: -0.5 | >65: -1
    The season cumulative is floored at 0 by the caller (document the choice).
    """
    raise NotImplementedError


def dynamic_portions(t: pd.Series) -> pd.Series:
    """Cumulative chill portions (Dynamic Model), same index as t.

    Follow chillR: TK = t_C + 273; xi = sr/(1+sr) with sr = exp(SLP*TETMLT*(TK-TETMLT)/TK);
    xs = (A0/A1)*exp((E1-E0)/TK); ak1 = A1*exp(-E1/TK). The intermediate E evolves hour by hour,
    and once E >= 1 a portion of E*xi is banked. Missing hours carry the state and add nothing.
    """
    raise NotImplementedError
