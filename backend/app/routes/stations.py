import json

from fastapi import APIRouter

from app.config import DATA_DIR
from app.schemas import StationsResponse

router = APIRouter(prefix="/api", tags=["stations"])


@router.get("/stations", response_model=StationsResponse)
def stations():
    doc = json.loads((DATA_DIR / "stations.json").read_text())
    maes = _validation_maes()
    return StationsResponse(stations=[{**s, "validation": maes.get(s["id"])} for s in doc["stations"]])


def _validation_maes() -> dict[int, dict]:
    """Per-station MAE from B's validation.json (empty until it exists)."""
    path = DATA_DIR / "validation.json"
    if not path.exists():
        return {}
    return {s["id"]: s["mae"] for s in json.loads(path.read_text()).get("stations", [])}
