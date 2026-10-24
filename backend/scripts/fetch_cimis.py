"""Download CIMIS hourly + daily temps for the validation stations into data/cimis/ (role B).

Resumable: one file per station-season (data/cimis/<station>_<season>_{hourly,daily}.json.gz);
files for finished seasons are skipped on re-runs, and every request is also kept in the L1 cache
(backend/.cache/http.sqlite), so a crash mid-season resumes at the month it stopped on. Retries
with backoff, and falls back to monthly chunks if a season-sized request is refused. Requests are
clamped to each station's service dates from data/stations.json. Needs CIMIS_KEY in the repo-root .env.

    cd backend
    python scripts/fetch_cimis.py --probe     # check the key and the response shape (2 requests)
    python scripts/fetch_cimis.py             # all 9 stations, seasons 2015-2025
    python scripts/fetch_cimis.py --stations 6 39 5 --seasons 2022-2025 --scopes hourly

Files keep the API's shape (Data > Providers > Records, trimmed to date, hour and temperature)
plus a "_meta" block, so app.sources.cimis.parse_hourly / parse_daily read them directly.
"""
import argparse
import gzip
import json
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so `app` imports when run as a script

from app import config  # noqa: E402
from app.calc.seasons import season_label  # noqa: E402
from app.sources import cache, cimis  # noqa: E402

DEFAULT_STATIONS = [6, 70, 71, 39, 5, 12, 244, 250, 222]
DEFAULT_SEASONS = "2015-2025"
SCOPES = ("hourly", "daily")
OUT_DIR = config.DATA_DIR / "cimis"
STATIONS_PATH = config.DATA_DIR / "stations.json"
DEFAULT_WORKERS = 3

_print_lock = threading.Lock()


def log(message: str) -> None:
    with _print_lock:
        print(message, flush=True)


@dataclass(frozen=True)
class Task:
    station: int
    season: int
    scope: str  # "hourly" | "daily"
    start: date
    end: date
    complete: bool  # nothing left to come for this range, so the file never needs refreshing

    @property
    def filename(self) -> str:
        return f"{self.station}_{self.season}_{self.scope}.json.gz"

    @property
    def label(self) -> str:
        return f"#{self.station} {season_label(self.season)} {self.scope}"


@dataclass
class RunState:
    """Shared between worker threads. Races are harmless: the worst case is one extra request."""

    hourly_needs_chunks: bool = False
    auth_failed: bool = False
    requests: int = 0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def count_request(self) -> None:
        with self.lock:
            self.requests += 1


def parse_seasons(text: str) -> list[int]:
    """"2015-2025" -> [2015, ..., 2025]; "2023" -> [2023]. Seasons are named by their start year."""
    if "-" in text:
        first, last = (int(part) for part in text.split("-", 1))
        if last < first:
            raise argparse.ArgumentTypeError(f"season range {text} runs backwards")
        return list(range(first, last + 1))
    return [int(text)]


def load_station_meta(path: Path = STATIONS_PATH) -> dict[int, dict]:
    return {s["id"]: s for s in json.loads(path.read_text())["stations"]}


def plan_tasks(
    stations: list[int], seasons: list[int], scopes: list[str], meta: dict[int, dict], today: date
) -> tuple[list[Task], list[str]]:
    """One task per station-season-scope, clamped to the station's service dates and to yesterday.

    Returns (tasks, notes) where notes explain station-seasons with nothing to fetch.
    """
    tasks, notes = [], []
    yesterday = today - timedelta(days=1)
    for station in stations:
        info = meta.get(station)
        if info is None:
            notes.append(f"#{station}: not in stations.json, so its service dates aren't checked")
        for season in seasons:
            start, end = date(season, 9, 1), date(season + 1, 8, 31)
            if info is not None:
                start = max(start, date.fromisoformat(info["connect_date"]))
                if info.get("disconnect_date"):
                    end = min(end, date.fromisoformat(info["disconnect_date"]))
            complete = end < today
            end = min(end, yesterday)
            if start > end:
                notes.append(f"#{station} {season_label(season)}: station not reporting then, skipped")
                continue
            for scope in scopes:
                tasks.append(Task(station, season, scope, start, end, complete))
    return tasks, notes


def fetch_range(
    task: Task, key: str, api: str, client: httpx.Client, state: RunState, use_cache: bool = True
) -> list[dict]:
    """All records for the task: one request for the whole range, else monthly chunks."""
    hourly = task.scope == "hourly"

    def one(start: date, end: date) -> dict:
        def fetch() -> dict:
            state.count_request()
            return cimis.fetch_station(task.station, start, end, hourly, key, api, client)

        if not use_cache:
            return fetch()
        # The key is never part of the cache key.
        cache_key = f"cimis:{api}:{task.station}:{task.scope}:{start}:{end}"
        ttl = cache.FOREVER if task.complete else cache.FORECAST_TTL_SECONDS
        value, _stale = cache.get_or_fetch(cache_key, fetch, ttl)
        return value

    if not (hourly and state.hourly_needs_chunks):
        try:
            return cimis.records(one(task.start, task.end))
        except cimis.CimisAuthError:
            raise
        except cimis.CimisError as e:
            if hourly and (e.code == cimis.VOLUME_ERROR or e.status == 400):
                state.hourly_needs_chunks = True  # every other hourly season will be refused too
            log(f"  {task.label}: whole-range request refused ({e}); fetching month by month")

    out: list[dict] = []
    for start, end in cimis.month_chunks(task.start, task.end):
        out.extend(cimis.records(one(start, end)))
    return out


def slim(records: list[dict], scope: str) -> list[dict]:
    """Keep only what parse_hourly / parse_daily read, so the committed files stay small."""
    items = (cimis.HOURLY_FIELD,) if scope == "hourly" else cimis.DAILY_FIELDS
    out = []
    for r in records:
        row = {"Date": cimis.field(r, "Date")}
        if scope == "hourly":
            row["Hour"] = cimis.field(r, "Hour")
        for name in items:
            item = cimis.field(r, name)
            if isinstance(item, dict):
                row[name] = {"Value": cimis.field(item, "Value"), "Qc": cimis.field(item, "Qc")}
        out.append(row)
    out.sort(key=lambda row: (str(row["Date"]), str(row.get("Hour", ""))))
    return out


def build_file(task: Task, records: list[dict], api: str) -> dict:
    rows = slim(records, task.scope)
    return {
        "_meta": {
            "source": "CIMIS (et.water.ca.gov)",
            "api": api,
            "station": task.station,
            "season": task.season,
            "label": season_label(task.season),
            "scope": task.scope,
            "items": cimis.HOURLY_ITEMS if task.scope == "hourly" else cimis.DAILY_ITEMS,
            "unit": "F",
            "start": task.start.isoformat(),
            "end": task.end.isoformat(),
            "complete": task.complete,
            "records": len(rows),
            "fetched_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        },
        "Data": {"Providers": [{"Name": "cimis", "Records": rows}]},
    }


def coverage(task: Task, payload: dict) -> str:
    """One line on how complete the data is, e.g. "8,710/8,784 hours (99.2%)"."""
    days = (task.end - task.start).days + 1
    if task.scope == "hourly":
        frame = cimis.parse_hourly(payload)
        have, expected, unit = int(frame["temp_f"].notna().sum()), days * 24, "hours"
    else:
        frame = cimis.parse_daily(payload)
        have = int((frame["tmax_f"].notna() & frame["tmin_f"].notna()).sum())
        expected, unit = days, "days"
    return f"{have:,}/{expected:,} {unit} ({100 * have / expected:.1f}%)"


def write_gz(path: Path, payload: dict) -> None:
    """Atomic write (a crash never leaves a half file that a re-run would skip). mtime=0 keeps
    re-fetched files byte-identical, so git only sees real data changes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    body = gzip.compress(json.dumps(payload, separators=(",", ":")).encode(), mtime=0)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(body)
    os.replace(tmp, path)


def run_task(
    task: Task, key: str, api: str, client: httpx.Client, state: RunState, out_dir: Path, use_cache: bool = True
) -> str:
    if state.auth_failed:
        raise cimis.CimisAuthError("skipped: CIMIS rejected the key")
    try:
        records = fetch_range(task, key, api, client, state, use_cache)
    except cimis.CimisAuthError:
        state.auth_failed = True
        raise
    if not records:
        raise cimis.CimisError("CIMIS returned no records")
    payload = build_file(task, records, api)
    summary = coverage(task, payload)
    write_gz(out_dir / task.filename, payload)
    return summary


def probe(key: str, api: str | None, client: httpx.Client) -> int:
    """Check the key and show the response shape for one day of hourly data at Davis."""
    api = api or cimis.detect_api(key, client)
    log(f"Key accepted by the '{api}' API.")
    day = date(2024, 1, 15)
    raw = cimis.fetch_station(6, day, day, hourly=True, key=key, api=api, client=client)
    rows = cimis.records(raw)
    log(f"Top-level keys: {list(raw)}")
    log(f"Records for Davis #6 on {day}: {len(rows)} (expect 24)")
    if rows:
        log("First record: " + json.dumps(rows[0]))
        frame = cimis.parse_hourly(raw)
        log(f"Parsed: {frame['temp_f'].notna().sum()} hourly temps, {frame.index[0]} to {frame.index[-1]}")
        log(frame.head(3).to_string())
    return 0 if len(rows) else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stations", type=int, nargs="+", default=DEFAULT_STATIONS)
    parser.add_argument("--seasons", type=parse_seasons, default=parse_seasons(DEFAULT_SEASONS),
                        help=f"season start years, e.g. 2023 or {DEFAULT_SEASONS} (the default)")
    parser.add_argument("--scopes", nargs="+", choices=SCOPES, default=list(SCOPES))
    parser.add_argument("--api", choices=cimis.APIS, help="skip detection (default: detect from the key)")
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="parallel requests to CIMIS")
    parser.add_argument("--force", action="store_true", help="re-download files that already exist")
    parser.add_argument("--probe", action="store_true", help="check the key and response shape, then stop")
    args = parser.parse_args(argv)

    key = config.CIMIS_KEY.strip()
    if not key:
        log("CIMIS_KEY is empty. Add it to the repo-root .env (see .env.example), then re-run.")
        return 2

    with httpx.Client(timeout=cimis.TIMEOUT_SECONDS) as client:
        try:
            if args.probe:
                return probe(key, args.api, client)
            api = args.api or cimis.detect_api(key, client)
        except cimis.CimisError as e:
            log(str(e))
            return 1
        log(f"Using the '{api}' CIMIS API.")

        tasks, notes = plan_tasks(args.stations, args.seasons, args.scopes, load_station_meta(), date.today())
        for note in notes:
            log(note)
        todo = [t for t in tasks if args.force or not (t.complete and (OUT_DIR / t.filename).exists())]
        log(f"{len(tasks)} station-season files: {len(tasks) - len(todo)} already fetched, {len(todo)} to go.")

        state = RunState()
        failures: list[tuple[Task, str]] = []
        started = time.perf_counter()

        def work(task: Task) -> None:
            try:
                summary = run_task(task, key, api, client, state, OUT_DIR, use_cache=not args.force)
                log(f"ok    {task.label}: {summary}")
            except Exception as e:  # keep going; a re-run resumes
                message = str(e).replace(key, "***")
                failures.append((task, message))
                log(f"FAIL  {task.label}: {message}")

        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            list(pool.map(work, todo))

    minutes = (time.perf_counter() - started) / 60
    log(f"Done in {minutes:.1f} min, {state.requests} CIMIS requests, {len(todo) - len(failures)} files written.")
    if failures:
        log(f"{len(failures)} failed. Re-run the same command to retry just those:")
        for task, error in failures:
            log(f"  {task.label}: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
