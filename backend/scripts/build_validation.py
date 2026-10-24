"""Build data/validation.json and data/bias_tables.json from committed CIMIS data (role B).

For each station and season: totals from CIMIS (truth), raw gridded, and corrected gridded,
where station X is corrected only from the other stations' bias tables (leave-one-station-out),
the situation a real orchard pin is in. Totals come from the app's own season math
(build_point._season_daily, default settings: almond GDD, portions from Sep 1, chill hours and
Utah Nov 1 - end Feb, GDD from Jan 1), so the errors are errors in numbers the app shows.

Gridded data is Open-Meteo's archive at each station's snapped 0.1° cell (what a pin there gets),
through the cached client. All three series are compared on the same hours: hours CIMIS is
missing (after the app's gap filling) are dropped from the gridded series too.

Also written, for the team (the API ignores these keys):
- "models": Open-Meteo best_match vs era5_land vs ecmwf_ifs on recent seasons (--models)
- "durham": Durham's own table on held-out seasons (what the app does near Durham), and the
  nearest-station baseline (Biggs readings used as Durham's)

    cd backend && python scripts/build_validation.py            # ~100 archive requests, cached forever
    python scripts/build_validation.py --models                # + model check (~70 more requests)

Output matches schemas.ValidationResponse; bias_tables.json matches what build_point reads.
"""
import argparse
import gzip
import json
import sys
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so `app` imports when run as a script

from app.calc import gaps  # noqa: E402
from app.calc.crops import CROPS  # noqa: E402
from app.calc.seasons import season_label  # noqa: E402
from app.config import DATA_DIR, PST  # noqa: E402
from app.pipeline import build_point  # noqa: E402
from app.pipeline.timeseries import snap, to_pst  # noqa: E402
from app.sources import cimis, openmeteo  # noqa: E402
from app.validation import metrics  # noqa: E402
from app.validation.bias import BiasCandidate, apply_bias, blend_tables, fit_bias_table  # noqa: E402

METRICS = build_point.METRICS
CIMIS_DIR = DATA_DIR / "cimis"
VALIDATION_PATH = DATA_DIR / "validation.json"
BIAS_TABLES_PATH = DATA_DIR / "bias_tables.json"
STATIONS_PATH = DATA_DIR / "stations.json"
DEFAULT_SEASONS = (2015, 2025)
# What the app's correction touches (build_point). Correcting every metric made chill portions,
# chill hours and Utah worse in leave-one-station-out tests (also tried: month-only offsets,
# 3-hour blocks, hour-averaging, quantile mapping); GDD error roughly halves with any of them.
CORRECTED_METRICS = ("gdd",)
MIN_COVERAGE = 0.85  # share of a season's hours CIMIS must have for that season to count
MODEL_CHECK = ("best_match", "era5_land", "ecmwf_ifs")
MODEL_CHECK_SEASONS = (2023, 2024)
DURHAM, BIGGS = 12, 244
PACE_SECONDS = 3.0  # between uncached Open-Meteo requests (free tier: 600 calls/min, long ranges count extra)
SETTINGS = build_point.Settings(
    crop="almond",
    base_f=CROPS["almond"]["base_f"],
    upper_f=CROPS["almond"]["upper_f"],
    portions_start="09-01",
    hours_start="11-01",
    gdd_start="01-01",
)


def log(msg: str) -> None:
    print(msg, flush=True)


@dataclass
class StationData:
    info: dict
    cimis: pd.Series  # hourly °F, PST, gap-filled like the app
    seasons: list[int]  # seasons with enough CIMIS coverage


# --- loading ----------------------------------------------------------------------------------


def season_hours(season: int) -> pd.DatetimeIndex:
    start, end = build_point.season_bounds(season)
    return pd.date_range(pd.Timestamp(start, tz=PST), pd.Timestamp(end, tz=PST) + pd.Timedelta(hours=23), freq="h")


def load_cimis(station: int, seasons: list[int], cimis_dir: Path = CIMIS_DIR) -> pd.Series:
    """All committed hourly CIMIS data for a station on a complete PST hourly index, gap-filled."""
    parts = []
    for s in seasons:
        path = cimis_dir / f"{station}_{s}_hourly.json.gz"
        if path.exists():
            parts.append(cimis.parse_hourly(json.loads(gzip.decompress(path.read_bytes())))["temp_f"])
    if not parts:
        return pd.Series(dtype=float, index=pd.DatetimeIndex([], tz=PST))
    t = pd.concat(parts).sort_index()
    t = t[~t.index.duplicated(keep="last")]
    t = t.reindex(pd.date_range(t.index.min(), t.index.max(), freq="h"))
    return gaps.fill_gaps(t)[0]


def coverage(t: pd.Series, season: int) -> float:
    hours = season_hours(season)
    return float(t.reindex(hours).notna().mean())


def fetch_gridded(lat: float, lon: float, seasons: list[int], model: str = "best_match", pace: float = PACE_SECONDS) -> pd.Series:
    """Open-Meteo archive hourly °F at the snapped cell, PST, gap-filled like the app."""
    glat, glon = snap(lat, lon)
    parts = []
    for s in seasons:
        start, end = build_point.season_bounds(s)
        started = time.perf_counter()
        series = _fetch_with_backoff(glat, glon, start - timedelta(days=1), end + timedelta(days=1), model)
        parts.append(series)
        if time.perf_counter() - started > 0.3:  # it went to the network, not the cache
            time.sleep(pace)
    t = to_pst(pd.concat(parts).sort_index())
    t = t[~t.index.duplicated(keep="first")]
    t = t.reindex(pd.date_range(t.index.min(), t.index.max(), freq="h"))
    return gaps.fill_gaps(t)[0]


def _fetch_with_backoff(lat, lon, start, end, model, waits=(30, 60, 120)) -> pd.Series:
    for wait in (*waits, None):
        try:
            return openmeteo.fetch_archive_hourly(lat, lon, start, end, model=model)
        except openmeteo.OpenMeteoError as e:
            if wait is None or not any(k in str(e).lower() for k in ("429", "limit", "too many")):
                raise
            log(f"  Open-Meteo rate limit; waiting {wait} s ({e})")
            time.sleep(wait)


# --- metrics ----------------------------------------------------------------------------------


def season_totals(t: pd.Series, season: int, heat: pd.Series | None = None) -> dict[str, float] | None:
    """End-of-season totals the app would show (default settings): chill from t, GDD from heat.

    build_point applies the station correction to heat only (see CORRECTED_METRICS), so for the
    corrected case t is the raw gridded series and heat the corrected one.
    """
    work = pd.DataFrame({"temp_f": t, "heat_f": t if heat is None else heat, "source": "archive", "filled": False})
    daily = build_point._season_daily(work, season, SETTINGS)
    if daily.empty:
        return None
    last = daily.iloc[-1]
    return {m: round(float(last[m]), 1) for m in METRICS}


def compare(truth: pd.Series, raw: pd.Series, corrected: pd.Series, season: int, heat_only: bool = True) -> dict | None:
    """Totals for one season, all three on the hours CIMIS has.

    heat_only=True scores what the app serves (correction on GDD only); False corrects every
    metric, which is how we found the correction hurts chill.
    """
    hours = season_hours(season)
    observed = truth.reindex(hours)
    mask = observed.isna()
    r, c = raw.reindex(hours).mask(mask), corrected.reindex(hours).mask(mask)
    entry = {"season": season_label(season)}
    for name, totals in (
        ("cimis", season_totals(observed, season)),
        ("raw", season_totals(r, season)),
        ("corrected", season_totals(r, season, heat=c) if heat_only else season_totals(c, season)),
    ):
        if totals is None:
            return None
        entry[name] = totals
    return entry


def mae_by_metric(entries: list[dict], against: str = "cimis") -> dict[str, dict[str, float]]:
    out = {}
    for m in METRICS:
        truth = [e[against][m] for e in entries]
        out[m] = {
            "raw_mae": round(metrics.mae([e["raw"][m] for e in entries], truth), 2),
            "corrected_mae": round(metrics.mae([e["corrected"][m] for e in entries], truth), 2),
        }
    return out


def distance_km(a: dict, b: dict) -> float:
    return build_point._km(a["lat"], a["lon"], b["lat"], b["lon"])


# --- main steps ---------------------------------------------------------------------------------


def leave_one_out(target: dict, tables: dict[int, tuple[pd.DataFrame, int]], infos: dict[int, dict]):
    """The blended table for `target` from every other station, plus who it used."""
    candidates = [
        BiasCandidate(sid, table, distance_km(target, infos[sid]), infos[sid]["active"], n)
        for sid, (table, n) in tables.items()
        if sid != target["id"]
    ]
    result = blend_tables(candidates)
    if result is None:
        return None, []
    table, weights = result
    used = [
        {"id": c.station_id, "name": infos[c.station_id]["name"], "distance_km": round(c.distance_km, 1), "weight": round(w, 3)}
        for c, w in sorted(zip(candidates, weights), key=lambda cw: -cw[1])
        if w > 0
    ]
    return table, used


def durham_extras(data: dict[int, StationData], gridded: dict[int, pd.Series]) -> dict:
    """Durham's own table on held-out seasons, and Biggs's readings standing in for Durham's."""
    out = {}
    if DURHAM not in data:
        return out
    d = data[DURHAM]
    entries, all_entries = [], []
    for held_out in d.seasons:
        hours = season_hours(held_out)
        g, c = gridded[DURHAM], d.cimis
        table = fit_bias_table(g[~g.index.isin(hours)], c[~c.index.isin(hours)])
        corrected = apply_bias(gridded[DURHAM], table)
        e = compare(d.cimis, gridded[DURHAM], corrected, held_out)
        e_all = compare(d.cimis, gridded[DURHAM], corrected, held_out, heat_only=False)
        if e and e_all:
            entries.append(e)
            all_entries.append(e_all)
    if entries:
        out["own_table_held_out"] = {
            "about": "Durham corrected with its own table fit on its other seasons: the live app's setup near Durham.",
            "mae": mae_by_metric(entries),
            "mae_if_every_metric_corrected": mae_by_metric(all_entries),
            "seasons": entries,
        }
    if BIGGS in data:
        rows = []
        for s in sorted(set(d.seasons) & set(data[BIGGS].seasons)):
            hours = season_hours(s)
            truth = d.cimis.reindex(hours)
            biggs = data[BIGGS].cimis.reindex(hours)
            both = truth.notna() & biggs.notna()
            a, b = season_totals(truth.where(both), s), season_totals(biggs.where(both), s)
            if a and b:
                rows.append({"season": season_label(s), "durham": a, "biggs": b})
        if rows:
            out["nearest_station_baseline"] = {
                "about": "Biggs #244 CIMIS readings (25 km away) used as Durham's: a grower's alternative when Durham closed.",
                "mae": {m: round(metrics.mae([r["biggs"][m] for r in rows], [r["durham"][m] for r in rows]), 2) for m in METRICS},
                "seasons": rows,
            }
    return out


def model_check(data: dict[int, StationData], pace: float) -> dict:
    """Hourly MAE and chill-portion MAE (raw, uncorrected) for each Open-Meteo model."""
    out = {}
    for model in MODEL_CHECK:
        hourly_err, cp = [], []
        for sid, d in data.items():
            seasons = [s for s in MODEL_CHECK_SEASONS if s in d.seasons]
            if not seasons:
                continue
            log(f"  {model} #{sid}")
            g = fetch_gridded(d.info["lat"], d.info["lon"], seasons, model=model, pace=pace)
            for s in seasons:
                hours = season_hours(s)
                truth, grid = d.cimis.reindex(hours), g.reindex(hours)
                ok = truth.notna() & grid.notna()
                hourly_err.append(float((grid[ok] - truth[ok]).abs().mean()))
                e = compare(d.cimis, g, g, s)
                if e:
                    cp.append(abs(e["raw"]["chill_portions"] - e["cimis"]["chill_portions"]))
        out[model] = {
            "hourly_temp_mae_f": round(float(np.mean(hourly_err)), 2) if hourly_err else None,
            "chill_portions_mae": round(float(np.mean(cp)), 2) if cp else None,
            "station_seasons": len(cp),
        }
    return out


def build(stations: list[int], seasons: list[int], models: bool, pace: float) -> tuple[dict, dict]:
    infos = {s["id"]: s for s in json.loads(STATIONS_PATH.read_text())["stations"]}
    data: dict[int, StationData] = {}
    skipped = []
    for sid in stations:
        t = load_cimis(sid, seasons)
        good = []
        for s in seasons:
            c = coverage(t, s) if len(t) else 0.0
            if c >= MIN_COVERAGE:
                good.append(s)
            elif c > 0:
                skipped.append({"station": sid, "season": season_label(s), "coverage": round(c, 3)})
        if good:
            data[sid] = StationData(infos[sid], t, good)
            log(f"#{sid} {infos[sid]['name']}: {len(good)} seasons of CIMIS data")

    gridded = {}
    for sid, d in data.items():
        log(f"Open-Meteo best_match for #{sid} {d.info['name']} ({len(d.seasons)} seasons)")
        gridded[sid] = fetch_gridded(d.info["lat"], d.info["lon"], d.seasons, pace=pace)

    tables = {sid: (fit_bias_table(gridded[sid], data[sid].cimis), len(data[sid].seasons)) for sid in data}

    station_out, all_entries, every_metric = [], [], []
    for sid, d in data.items():
        table, used = leave_one_out(d.info, tables, infos)
        corrected = apply_bias(gridded[sid], table) if table is not None else gridded[sid]
        entries = [e for s in d.seasons if (e := compare(d.cimis, gridded[sid], corrected, s))]
        all_entries += entries
        every_metric += [e for s in d.seasons if (e := compare(d.cimis, gridded[sid], corrected, s, heat_only=False))]
        station_out.append({
            "id": sid,
            "name": d.info["name"],
            "mae": mae_by_metric(entries),
            "seasons": entries,
            "corrected_with": used,
        })
        m = station_out[-1]["mae"]["chill_portions"]
        log(f"#{sid} {d.info['name']}: chill portions MAE raw {m['raw_mae']} -> corrected {m['corrected_mae']}")

    validation = {
        "built_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "summary": mae_by_metric(all_entries),
        "stations": station_out,
        "method": {
            "gridded": "Open-Meteo archive, model best_match, at each station's 0.1-degree cell",
            "correction": "leave-one-station-out: each station corrected only from the other stations' 12x24 tables (IDW, 150 km, closed-station rule)",
            "corrected_metrics": list(CORRECTED_METRICS),
            "why": "Correcting every metric made chill worse (see mae_if_every_metric_corrected); GDD error roughly halves. So the app corrects heat only and chill uses the raw gridded temperatures.",
            "mae_if_every_metric_corrected": mae_by_metric(every_metric),
            "settings": {"crop": SETTINGS.crop, "portions_start": SETTINGS.portions_start, "hours_start": SETTINGS.hours_start, "gdd_start": SETTINGS.gdd_start},
            "seasons": [season_label(s) for s in seasons],
            "min_coverage": MIN_COVERAGE,
            "station_seasons": len(all_entries),
            "skipped": skipped,
        },
        "durham": durham_extras(data, gridded),
    }
    if models:
        log("Model check")
        validation["models"] = model_check(data, pace)

    bias_tables = {
        "built_at": validation["built_at"],
        "about": "Mean (CIMIS - Open-Meteo best_match) °F by month (rows 1-12) and PST hour (columns 0-23), fit on every season of each station.",
        "stations": {str(sid): {"table": table.round(3).to_numpy().tolist(), "seasons": n} for sid, (table, n) in tables.items()},
    }
    return validation, bias_tables


def parse_seasons(text: str) -> list[int]:
    if "-" in text:
        a, b = (int(x) for x in text.split("-", 1))
        return list(range(a, b + 1))
    return [int(text)]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stations", type=int, nargs="+", default=[6, 70, 71, 39, 5, 12, 244, 250, 222])
    parser.add_argument("--seasons", type=parse_seasons, default=list(range(DEFAULT_SEASONS[0], DEFAULT_SEASONS[1] + 1)))
    parser.add_argument("--models", action="store_true", help="also score era5_land and ecmwf_ifs")
    parser.add_argument("--pace", type=float, default=PACE_SECONDS, help="seconds between uncached requests")
    args = parser.parse_args(argv)

    started = time.perf_counter()
    validation, tables = build(args.stations, args.seasons, args.models, args.pace)
    VALIDATION_PATH.write_text(json.dumps(validation, indent=1) + "\n")
    BIAS_TABLES_PATH.write_text(json.dumps(tables) + "\n")
    s = validation["summary"]
    log(f"Wrote {VALIDATION_PATH.name} and {BIAS_TABLES_PATH.name} in {(time.perf_counter() - started) / 60:.1f} min")
    for m in METRICS:
        log(f"  {m:15} MAE raw {s[m]['raw_mae']:8.2f}  corrected {s[m]['corrected_mae']:8.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
