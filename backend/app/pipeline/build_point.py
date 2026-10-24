"""Assemble the /api/point response: fetch, normalize, correct, compute, shape."""


def build_point(
    lat: float,
    lon: float,
    season: int,
    crop: str,
    portions_start: str,
    hours_start: str,
    gdd_start: str,
    corrected: bool,
) -> dict:
    """Return a dict matching schemas.PointResponse.

    Steps: snap -> fetch archive + forecast (via cache) -> merge -> to PST -> calc.gaps.fill_gaps
    -> validation.bias correction -> calc models per season -> history, forecast, climatology.
    """
    raise NotImplementedError
