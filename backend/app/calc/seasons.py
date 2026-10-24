"""Season windows. A season runs Sep 1 to Aug 31; season 2025 is labeled "2025-26"."""
import calendar
from datetime import date


def season_label(season: int) -> str:
    """2025 -> "2025-26"."""
    return f"{season}-{(season + 1) % 100:02d}"


def season_window(season: int, start_mmdd: str) -> tuple[date, date]:
    """(start, end) for a metric inside a season.

    A start month of Sep-Dec falls in `season`, Jan-Aug in `season + 1`. End is always Aug 31
    of season + 1. "02-29" in a non-leap year becomes Feb 28.
    (The /api/point pipeline stops chill hours and Utah at the end of February, FNRIC's window.)
    """
    month, day = (int(part) for part in start_mmdd.split("-"))
    year = season if month >= 9 else season + 1
    if month == 2 and day == 29 and not calendar.isleap(year):
        day = 28
    return date(year, month, day), date(season + 1, 8, 31)
