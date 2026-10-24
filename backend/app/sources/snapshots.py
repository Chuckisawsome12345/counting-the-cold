"""L3 fallback: full /api/point responses committed under data/snapshots/*.json.gz.

Served when DEMO_MODE=1, or when a live fetch fails and the L1 cache has nothing.
"""


def snapshot_name(lat: float, lon: float, season: int) -> str:
    """File stem for a snapped cell and season, e.g. "39.6_-121.8_2025"."""
    raise NotImplementedError


def load_snapshot(lat: float, lon: float, season: int) -> dict | None:
    raise NotImplementedError


def save_snapshot(lat: float, lon: float, season: int, response: dict) -> None:
    raise NotImplementedError
