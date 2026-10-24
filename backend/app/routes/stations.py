import json

from fastapi import APIRouter

from app.config import DATA_DIR
from app.schemas import StationsResponse

router = APIRouter(prefix="/api", tags=["stations"])


@router.get("/stations", response_model=StationsResponse)
def stations():
    doc = json.loads((DATA_DIR / "stations.json").read_text())
    # TODO(A): attach each station's validation summary from data/validation.json.
    return StationsResponse(stations=doc["stations"])
