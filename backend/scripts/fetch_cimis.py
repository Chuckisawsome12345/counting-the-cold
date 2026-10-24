"""Download CIMIS hourly + daily temps for the validation stations into data/cimis/ (role B).

Resumable: one file per station-season (data/cimis/<station>_<season>_{hourly,daily}.json.gz);
existing files are skipped. Retries with backoff, and falls back to monthly chunks if a
season-sized request is refused. Needs CIMIS_KEY in the repo-root .env.

    python scripts/fetch_cimis.py --stations 6 70 71 39 5 12 244 250 222 --seasons 2015-2025
"""
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--stations", type=int, nargs="+", required=True)
    parser.add_argument("--seasons", required=True, help="e.g. 2015-2025 (season start years)")
    parser.parse_args()
    raise NotImplementedError


if __name__ == "__main__":
    main()
