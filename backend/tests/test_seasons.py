from datetime import date

from app.calc.seasons import season_label, season_window
from tests.helpers import stub


@stub
def test_label():
    assert season_label(2025) == "2025-26"


@stub
def test_fall_and_winter_starts():
    assert season_window(2025, "09-01") == (date(2025, 9, 1), date(2026, 8, 31))
    assert season_window(2025, "11-01") == (date(2025, 11, 1), date(2026, 8, 31))
    assert season_window(2025, "01-01") == (date(2026, 1, 1), date(2026, 8, 31))


@stub
def test_feb_29():
    assert season_window(2023, "02-29")[0] == date(2024, 2, 29)
    assert season_window(2024, "02-29")[0] == date(2025, 2, 28)
