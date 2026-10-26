"""Precompute one season's chill and heat on a Central Valley grid -> data/grid/<season>.json.

Runs offline, once per season, so the statewide map costs nothing at demo time. Each cell is one
season of hourly data (no history), fetched politely in sequence to stay inside Open-Meteo's
free-tier limits; everything lands in the L1 cache, so re-runs are fast.

    cd backend && python scripts/build_grid.py --season 2025
"""
import argparse
import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so `app` imports when run as a script

from app.config import DATA_DIR  # noqa: E402
from app.pipeline.build_point import build_point  # noqa: E402
from app.sources.openmeteo import OpenMeteoError  # noqa: E402

GRID_DIR = DATA_DIR / "grid"
METRICS = ("chill_portions", "chill_hours", "utah_units", "gdd")

# Rough outline of the Central Valley floor (Redding to Bakersfield), as (lat, lon) going clockwise.
VALLEY = [
    (40.60, -122.45), (40.40, -122.05), (39.60, -121.45), (38.60, -120.95), (37.60, -120.25),
    (36.80, -119.30), (35.80, -118.95), (35.00, -118.75), (34.95, -119.20), (35.50, -119.85),
    (36.60, -120.75), (37.60, -121.55), (38.50, -122.05), (39.50, -122.35),
]


def inside(lat: float, lon: float, polygon: list[tuple[float, float]] = VALLEY) -> bool:
    """Ray casting point-in-polygon test."""
    hit = False
    for (lat1, lon1), (lat2, lon2) in zip(polygon, polygon[1:] + polygon[:1]):
        if (lon1 > lon) != (lon2 > lon) and lat < (lat2 - lat1) * (lon - lon1) / (lon2 - lon1) + lat1:
            hit = not hit
    return hit


def grid_points(step: float = 0.25) -> list[tuple[float, float]]:
    lats = np.arange(34.75, 40.75 + step / 2, step)
    lons = np.arange(-122.5, -118.5 + step / 2, step)
    return [(round(float(a), 3), round(float(o), 3)) for a in lats for o in lons if inside(a, o)]


def build(season: int, step: float = 0.25, today: date | None = None, pause: float = 0.5, build=build_point) -> dict:
    cells = []
    points = grid_points(step)
    for i, (lat, lon) in enumerate(points, 1):
        try:
            p = build(lat, lon, season, "almond", "09-01", "11-01", "01-01", True, today=today, history_seasons=0)
        except OpenMeteoError as e:
            print(f"[{i}/{len(points)}] {lat},{lon}: skipped ({e})")
            continue
        cells.append({"lat": lat, "lon": lon, **{m: p["totals"][m] for m in METRICS}})
        print(f"[{i}/{len(points)}] {lat},{lon}: {p['totals']['chill_portions']} CP")
        time.sleep(pause)
    return {
        "season": f"{season}-{str(season + 1)[2:]}",
        "step_deg": step,
        "built_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "cells": cells,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--season", type=int, default=2025)
    parser.add_argument("--step", type=float, default=0.25)
    args = parser.parse_args()
    doc = build(args.season, args.step)
    GRID_DIR.mkdir(parents=True, exist_ok=True)
    path = GRID_DIR / f"{args.season}.json"
    path.write_text(json.dumps(doc, separators=(",", ":")) + "\n")
    print(f"wrote {path} ({len(doc['cells'])} cells)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
