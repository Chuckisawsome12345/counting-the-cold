"""Warm the L1 cache and write L3 snapshots for config.DEMO_PINS (role A).

Run at startup on Render and before judging:

    python scripts/prewarm.py --seasons 2025 2026
"""
import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seasons", type=int, nargs="+", default=[2025, 2026])
    parser.parse_args()
    raise NotImplementedError


if __name__ == "__main__":
    main()
