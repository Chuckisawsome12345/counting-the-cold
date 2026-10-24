"""Warm the L1 cache for config.DEMO_PINS and, with --snapshots, write L3 snapshots (role A).

Render runs it in the background at startup (see render.yaml) so the first judge's click is fast.
Before judging, refresh the committed snapshots from your laptop and commit them:

    cd backend && python scripts/prewarm.py --snapshots
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # so `app` imports when run as a script

from app.config import DEMO_PINS  # noqa: E402
from app.pipeline.build_point import build_point  # noqa: E402
from app.sources import snapshots  # noqa: E402
from app.sources.openmeteo import OpenMeteoError  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seasons", type=int, nargs="+", default=[2025, 2026])
    parser.add_argument("--snapshots", action="store_true", help="also write data/snapshots/ for DEMO_MODE")
    args = parser.parse_args()

    for name, (lat, lon) in DEMO_PINS.items():
        for season in args.seasons:
            for corrected in (True, False):
                t = time.perf_counter()
                try:
                    response = build_point(lat, lon, season, "almond", *snapshots.DEFAULT_STARTS, corrected)
                except NotImplementedError:
                    print("B's calc functions aren't implemented yet; nothing to warm.")
                    return 0
                except OpenMeteoError as e:
                    print(f"{name} {season}: Open-Meteo failed ({e}); skipping")
                    continue
                line = f"{name} {season} {'corrected' if corrected else 'raw'}: {time.perf_counter() - t:.1f}s"
                if args.snapshots:
                    line += f" -> {snapshots.save_snapshot(lat, lon, season, response, 'almond', corrected).name}"
                print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
