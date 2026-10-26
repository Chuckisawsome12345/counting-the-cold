from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app import config
from app.calc.crops import CROPS
from app.pipeline.build_point import build_point
from app.schemas import PointResponse
from app.sources import cache, snapshots
from app.sources.openmeteo import OpenMeteoError

router = APIRouter(prefix="/api", tags=["point"])


@router.get("/point", response_model=PointResponse)
def point(
    lat: float = Query(..., ge=32.0, le=42.1, description="Latitude, California only"),
    lon: float = Query(..., ge=-124.5, le=-114.0, description="Longitude, California only"),
    season: int = Query(2025, description="Season start year: 2025 = Sep 1 2025 to Aug 31 2026"),
    crop: str = Query("almond", description="Crop preset id from /api/crops"),
    portions_start: str = Query("09-01", pattern=r"^\d{2}-\d{2}$"),
    hours_start: str = Query("11-01", pattern=r"^\d{2}-\d{2}$"),
    gdd_start: str = Query("01-01", pattern=r"^\d{2}-\d{2}$"),
    corrected: bool = True,
):
    if crop not in CROPS:
        raise HTTPException(422, f"unknown crop {crop!r}; choose one of {sorted(CROPS)}")
    default_starts = (portions_start, hours_start, gdd_start) == snapshots.DEFAULT_STARTS

    if config.DEMO_MODE:
        snap_resp = snapshots.load_snapshot(lat, lon, season, crop, corrected) if default_starts else None
        if snap_resp is None:
            raise HTTPException(503, "Demo mode: this spot isn't preloaded. Try one of the demo pins.")
        return snap_resp

    today = date.today()
    args = (round(lat, 4), round(lon, 4), season, crop, portions_start, hours_start, gdd_start, corrected)
    try:
        return cache.remember(f"point:{args}:{today}", lambda: build_point(*args, today=today))
    except OpenMeteoError as e:
        snap_resp = snapshots.load_snapshot(lat, lon, season, crop, corrected) if default_starts else None
        if snap_resp is not None:
            snap_resp["quality"]["stale"] = True
            return snap_resp
        raise HTTPException(503, f"Weather data is unavailable right now ({e}). Try again in a minute.") from e
