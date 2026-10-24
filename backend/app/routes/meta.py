from fastapi import APIRouter

from app.calc.crops import CROPS
from app.config import DEMO_MODE
from app.schemas import CropsResponse, HealthResponse

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/health", response_model=HealthResponse)
def health():
    # TODO(A): report the real L1 entry count once sources/cache.py exists.
    return HealthResponse(ok=True, demo_mode=DEMO_MODE, cache_entries=0)


@router.get("/crops", response_model=CropsResponse)
def crops():
    return CropsResponse(crops=list(CROPS.values()))
