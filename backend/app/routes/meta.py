from fastapi import APIRouter

from app.calc.crops import CROPS
from app.config import DEMO_MODE
from app.schemas import CropsResponse, HealthResponse
from app.sources import cache

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health", response_model=HealthResponse)
def health():
    return HealthResponse(ok=True, demo_mode=DEMO_MODE, cache_entries=cache.entry_count())


@router.get("/crops", response_model=CropsResponse)
def crops():
    return CropsResponse(crops=list(CROPS.values()))
