"""(Stretch) Almond hull split prediction from GDD90 (Tombesi et al. 2010, FNRIC model).

GDD90 = degree days from full bloom to 90 days after, single-sine method. Thresholds and
per-cultivar regression coefficients come from the Tombesi 2010 paper linked on the FNRIC page.
"""
from datetime import date


def gdd90(daily_gdd_single_sine, bloom: date) -> float:
    raise NotImplementedError


def predict_hull_split(bloom: date, gdd90_value: float, cultivar: str) -> date:
    raise NotImplementedError
