"""Public, embeddable API: every model's season total for one location (our adoption path)."""
from fastapi import APIRouter, Query

from app.routes.point import point
from app.schemas import ModelsResponse

router = APIRouter(prefix="/api/v1", tags=["public API"])

ATTRIBUTION = (
    "Counting the Cold: Open-Meteo hourly temperatures, bias-corrected against CIMIS stations. "
    "Models as used by UC Davis FNRIC and UC IPM."
)


@router.get("/models", response_model=ModelsResponse, summary="Chill and heat totals for any California location")
def models(
    lat: float = Query(..., ge=32.0, le=42.1, description="Latitude, California only", examples=[39.64]),
    lon: float = Query(..., ge=-124.5, le=-114.0, description="Longitude, California only", examples=[-121.79]),
    season: int = Query(2025, description="Season start year: 2025 = Sep 1 2025 to Aug 31 2026"),
    crop: str = Query("almond", description="GDD preset from /api/crops (sets base and upper °F)"),
):
    """Season-to-date chill portions, chill hours, Utah units and growing degree days at one spot,
    with the model behind each number and the expected error from our station validation.

    Uses FNRIC's default windows: portions from Sep 1, chill hours and Utah Nov 1 to end of
    February, GDD from Jan 1.
    """
    p = point(lat, lon, season, crop, "09-01", "11-01", "01-01", True)
    s, st = p["season"], p["settings"]
    upper = f", upper {st['gdd_upper_f']:g} °F" if st["gdd_upper_f"] is not None else ""
    return {
        "mock": p["mock"],
        "location": p["location"],
        "season": s["label"],
        "as_of": s["as_of"],
        "complete": s["complete"],
        "corrected": p["correction"]["applied"],
        "models": {
            "chill_portions": {"value": p["totals"]["chill_portions"], "unit": "CP", "window_start": s["portions_start"],
                               "model": "Dynamic Model (Fishman et al. 1987), FNRIC's preferred chill model"},
            "chill_hours": {"value": p["totals"]["chill_hours"], "unit": "h", "window_start": s["hours_start"],
                            "model": "Hours between 32 and 45 °F, through end of February"},
            "utah_units": {"value": p["totals"]["utah_units"], "unit": "CU", "window_start": s["hours_start"],
                           "model": "Utah Model (Richardson et al. 1974), running total floored at 0"},
            "gdd": {"value": p["totals"]["gdd"], "unit": "°F-days", "window_start": s["gdd_start"],
                    "model": f"Average method, base {st['gdd_base_f']:g} °F{upper} ({st['crop']} preset, UC IPM thresholds)"},
        },
        "expected_error": p["correction"]["expected_error"],
        "nearest_station": p["nearest_station"],
        "attribution": ATTRIBUTION,
    }
