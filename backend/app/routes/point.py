import json
from datetime import date

from fastapi import APIRouter, HTTPException, Query

from app.calc.crops import CROPS
from app.config import DATA_DIR
from app.pipeline.build_point import build_point
from app.schemas import PointResponse
from app.sources import cache
from app.sources.openmeteo import OpenMeteoError

router = APIRouter(prefix="/api", tags=["point"])

# Synthetic responses from scripts/make_mock.py, served while B's calc functions are stubs.
MOCK_COMPLETE = DATA_DIR / "mock_point.json"  # season 2025-26
MOCK_CURRENT = DATA_DIR / "mock_point_current.json"  # season 2026-27, with forecast


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
    today = date.today()
    args = (round(lat, 4), round(lon, 4), season, crop, portions_start, hours_start, gdd_start, corrected)
    try:
        return cache.remember(f"point:{args}:{today}", lambda: build_point(*args, today=today))
    except NotImplementedError:
        return _mock(season)
    except OpenMeteoError as e:
        raise HTTPException(503, f"Weather data is unavailable right now ({e}). Try again in a minute.") from e


def _mock(season: int) -> dict:
    return json.loads((MOCK_CURRENT if season >= 2026 else MOCK_COMPLETE).read_text())
