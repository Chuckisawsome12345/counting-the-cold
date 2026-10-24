import json

from fastapi import APIRouter, Query

from app.config import DATA_DIR
from app.schemas import GridResponse, Metric

router = APIRouter(prefix="/api", tags=["grid"])

GRID_DIR = DATA_DIR / "grid"  # written offline by scripts/build_grid.py
UNITS = {"chill_portions": "CP", "chill_hours": "h", "utah_units": "CU", "gdd": "°F-days"}


@router.get("/grid", response_model=GridResponse)
def grid(
    season: int = Query(2025, description="Season start year"),
    metric: Metric = Query("chill_portions"),
):
    """One metric on the precomputed Central Valley grid, for the statewide map layer."""
    label = f"{season}-{str(season + 1)[2:]}"
    path = GRID_DIR / f"{season}.json"
    if not path.exists():
        return {"season": label, "metric": metric, "unit": UNITS[metric], "step_deg": 0.25, "built_at": None, "cells": []}
    doc = json.loads(path.read_text())
    return {
        "season": doc["season"],
        "metric": metric,
        "unit": UNITS[metric],
        "step_deg": doc["step_deg"],
        "built_at": doc["built_at"],
        "cells": [{"lat": c["lat"], "lon": c["lon"], "value": c[metric]} for c in doc["cells"]],
    }
