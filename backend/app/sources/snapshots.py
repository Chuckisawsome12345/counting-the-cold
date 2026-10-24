"""L3 fallback: full /api/point responses committed under data/snapshots/*.json.gz.

Served when DEMO_MODE=1, or when a live fetch fails and the L1 cache has nothing.
Only responses with the default start dates are snapshotted; scripts/prewarm.py writes them.
"""
import gzip
import json
from pathlib import Path

from app.config import DATA_DIR
from app.pipeline.timeseries import snap

SNAPSHOT_DIR: Path = DATA_DIR / "snapshots"
DEFAULT_STARTS = ("09-01", "11-01", "01-01")


def snapshot_name(lat: float, lon: float, season: int, crop: str = "almond", corrected: bool = True) -> str:
    """File stem for a snapped cell, season and setting, e.g. "39.6_-121.8_2025_almond_corrected"."""
    lat, lon = snap(lat, lon)
    return f"{lat:.1f}_{lon:.1f}_{season}_{crop}_{'corrected' if corrected else 'raw'}"


def load_snapshot(lat: float, lon: float, season: int, crop: str = "almond", corrected: bool = True) -> dict | None:
    path = SNAPSHOT_DIR / f"{snapshot_name(lat, lon, season, crop, corrected)}.json.gz"
    if not path.exists():
        return None
    return json.loads(gzip.decompress(path.read_bytes()))


def save_snapshot(lat: float, lon: float, season: int, response: dict, crop: str = "almond", corrected: bool = True) -> Path:
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    path = SNAPSHOT_DIR / f"{snapshot_name(lat, lon, season, crop, corrected)}.json.gz"
    # mtime=0 keeps the bytes stable, so re-running prewarm on unchanged data doesn't dirty git.
    path.write_bytes(gzip.compress(json.dumps(response, separators=(",", ":")).encode(), mtime=0))
    return path
