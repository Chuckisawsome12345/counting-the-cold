"""L1 cache: raw upstream responses in SQLite (backend/.cache/http.sqlite, gitignored), gzipped JSON.

TTLs: archive data and past CIMIS seasons never expire (ttl_seconds=None); forecasts expire after 1 h.
"""
from typing import Any, Callable

FORECAST_TTL_SECONDS = 3600


def get_or_fetch(key: str, fetch: Callable[[], Any], ttl_seconds: int | None) -> tuple[Any, bool]:
    """Return (value, stale).

    A fresh hit returns immediately. Otherwise call fetch() and store the result.
    If fetch() fails and an expired entry exists, return it with stale=True; else re-raise.
    """
    raise NotImplementedError


def entry_count() -> int:
    raise NotImplementedError
