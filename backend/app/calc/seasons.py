"""Season windows. A season runs Sep 1 to Aug 31; season 2025 is labeled "2025-26"."""
from datetime import date


def season_label(season: int) -> str:
    """2025 -> "2025-26"."""
    raise NotImplementedError


def season_window(season: int, start_mmdd: str) -> tuple[date, date]:
    """(start, end) for a metric inside a season.

    A start month of Sep-Dec falls in `season`, Jan-Aug in `season + 1`. End is always Aug 31
    of season + 1. "02-29" in a non-leap year becomes Feb 28.
    Open question: FNRIC stops chill hours at the end of February; decide whether to cap them.
    """
    raise NotImplementedError
