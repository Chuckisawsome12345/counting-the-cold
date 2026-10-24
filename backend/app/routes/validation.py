import json

from fastapi import APIRouter

from app.config import DATA_DIR
from app.schemas import ValidationResponse

router = APIRouter(prefix="/api", tags=["validation"])


@router.get("/validation", response_model=ValidationResponse)
def validation():
    path = DATA_DIR / "validation.json"  # written by scripts/build_validation.py
    if not path.exists():
        return ValidationResponse(built_at=None, summary={}, stations=[])
    return json.loads(path.read_text())
