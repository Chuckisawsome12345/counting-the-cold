"""Caches that keep the demo fast and keep us inside Open-Meteo's rate limits.

L1: raw upstream responses in SQLite (backend/.cache/http.sqlite, gitignored), gzipped JSON.
    Archive data and past CIMIS seasons never expire; forecasts expire after 1 h. If a refresh
    fails, the expired copy is served and marked stale.
L2: computed results (e.g. /api/point responses) in memory for 15 minutes.
"""
import gzip
import json
import sqlite3
import threading
import time
from collections import OrderedDict
from contextlib import closing
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlencode

from app.config import CACHE_DIR

FOREVER = None
FORECAST_TTL_SECONDS = 3600
RESULT_TTL_SECONDS = 900
RESULT_MAXSIZE = 256

DB_PATH: Path = CACHE_DIR / "http.sqlite"


def now() -> float:
    return time.time()


def cache_key(url: str, params: dict) -> str:
    """Stable key for a request: the URL plus its params in sorted order."""
    return f"{url}?{urlencode(sorted(params.items()))}"


def get_or_fetch(key: str, fetch: Callable[[], Any], ttl_seconds: int | None) -> tuple[Any, bool]:
    """Return (value, stale).

    A fresh hit returns immediately. Otherwise call fetch() and store the result (it must be
    JSON-serializable). If fetch() fails and an expired entry exists, return it with stale=True;
    else re-raise.
    """
    cached = _read(key)
    if cached is not None:
        fetched_at, value = cached
        if ttl_seconds is None or now() - fetched_at < ttl_seconds:
            return value, False
    try:
        value = fetch()
    except Exception:
        if cached is not None:
            return cached[1], True
        raise
    _write(key, value)
    return value, False


def entry_count() -> int:
    with closing(_connect()) as conn:
        return conn.execute("SELECT COUNT(*) FROM responses").fetchone()[0]


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS responses (key TEXT PRIMARY KEY, fetched_at REAL NOT NULL, body BLOB NOT NULL)"
    )
    return conn


def _read(key: str) -> tuple[float, Any] | None:
    with closing(_connect()) as conn:
        row = conn.execute("SELECT fetched_at, body FROM responses WHERE key = ?", (key,)).fetchone()
    if row is None:
        return None
    return row[0], json.loads(gzip.decompress(row[1]))


def _write(key: str, value: Any) -> None:
    body = gzip.compress(json.dumps(value).encode())
    with closing(_connect()) as conn, conn:
        conn.execute(
            "INSERT OR REPLACE INTO responses (key, fetched_at, body) VALUES (?, ?, ?)", (key, now(), body)
        )


_results: OrderedDict[str, tuple[float, Any]] = OrderedDict()
_results_lock = threading.Lock()


def remember(key: str, compute: Callable[[], Any], ttl_seconds: int = RESULT_TTL_SECONDS) -> Any:
    """L2: return a computed result from memory if it is younger than ttl_seconds, else compute it."""
    with _results_lock:
        hit = _results.get(key)
        if hit is not None and now() - hit[0] < ttl_seconds:
            _results.move_to_end(key)
            return hit[1]
    value = compute()
    with _results_lock:
        _results[key] = (now(), value)
        _results.move_to_end(key)
        while len(_results) > RESULT_MAXSIZE:
            _results.popitem(last=False)
    return value


def clear_results() -> None:
    with _results_lock:
        _results.clear()
