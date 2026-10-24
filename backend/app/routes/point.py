import json

from fastapi import APIRouter, Query

from app.config import DATA_DIR
from app.schemas import PointResponse

router = APIRouter(prefix="/api", tags=["point"])

# Synthetic responses from scripts/make_mock.py, served until the real pipeline lands.
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
    # TODO(A): replace the mock with pipeline.build_point.build_point(...).
    path = MOCK_CURRENT if season >= 2026 else MOCK_COMPLETE
    return json.loads(path.read_text())
