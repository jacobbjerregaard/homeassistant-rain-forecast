"""Unit tests for the pure rainfall parsing logic.

The parser is loaded directly from its file so these tests run without a
Home Assistant install.
"""

import importlib.util
import sys
from datetime import datetime
from pathlib import Path

_PARSER_PATH = (
    Path(__file__).resolve().parents[1]
    / "custom_components"
    / "rain_forecast"
    / "parser.py"
)
_spec = importlib.util.spec_from_file_location("rf_parser", _PARSER_PATH)
parser = importlib.util.module_from_spec(_spec)
# Register before exec so @dataclass can resolve the module via sys.modules.
sys.modules["rf_parser"] = parser
_spec.loader.exec_module(parser)
build_rain_data = parser.build_rain_data

NOW = datetime(2026, 6, 17, 12, 0, 0)


def _build_forecast() -> dict:
    daily = {
        "time": ["2026-06-15", "2026-06-16", "2026-06-17", "2026-06-18"],
        "precipitation_sum": [2.0, 3.0, 5.0, 1.0],
        "precipitation_probability_max": [50, 60, 80, 20],
        "rain_sum": [2.0, 3.0, 5.0, 1.0],
        "precipitation_hours": [4, 5, 6, 2],
    }
    times: list[str] = []
    precip: list[float] = []
    for hour in range(24):
        times.append(f"2026-06-17T{hour:02d}:00")
        if hour == 10:
            precip.append(1.0)
        elif hour == 11:
            precip.append(0.5)
        elif hour == 14:
            precip.append(2.0)
        else:
            precip.append(0.0)
    for hour in range(13):
        times.append(f"2026-06-18T{hour:02d}:00")
        precip.append(0.0)
    hourly = {
        "time": times,
        "precipitation": precip,
        "precipitation_probability": [0] * len(times),
        "rain": precip,
        "showers": [0.0] * len(times),
    }
    current = {"precipitation": 0.0, "rain": 0.0, "showers": 0.0, "weather_code": 0}
    return {"daily": daily, "hourly": hourly, "current": current}


def _build_archive() -> dict:
    return {
        "daily": {
            "time": [
                "2026-06-11",
                "2026-06-12",
                "2026-06-13",
                "2026-06-14",
                "2026-06-15",
            ],
            # 2026-06-15 set high on purpose; the fresher forecast must win.
            "precipitation_sum": [1.0, 1.0, 1.0, 1.0, 99.0],
        }
    }


def _data():
    return build_rain_data(_build_forecast(), _build_archive(), NOW, 2, 0.1)


def test_forecast_values():
    data = _data()
    assert data.forecast_today == 5.0
    assert data.forecast_tomorrow == 1.0
    assert data.probability_today == 80
    assert data.probability_tomorrow == 20


def test_today_so_far_and_current():
    data = _data()
    assert data.today_so_far == 1.5  # 10:00 (1.0) + 11:00 (0.5)
    assert data.current_precipitation == 0.0


def test_next_windows():
    data = _data()
    assert data.next_hour == 0.0
    assert data.next_24h == 2.0  # only the 14:00 spike falls in the window


def test_rain_soon_reports_the_earliest_possible_onset():
    """The 14:00 stamp covers 13:00-14:00, so rain may start in 60 min, not 120."""
    data = _data()
    assert data.rain_soon is True
    assert data.minutes_until_rain == 60
    assert data.rain_soon_amount == 2.0


def test_rain_soon_is_zero_minutes_when_the_hour_is_already_open():
    """At 13:30 the rainy 14:00 window has already started."""
    data = build_rain_data(
        _build_forecast(), _build_archive(), datetime(2026, 6, 17, 13, 30), 2, 0.1
    )
    assert data.rain_soon is True
    assert data.minutes_until_rain == 0


def test_history_prefers_forecast_over_archive():
    data = _data()
    assert data.yesterday == 3.0
    # 11-14 (archive 1.0 each) + 15 (forecast 2.0) + 16 (forecast 3.0) + today (1.5)
    assert data.last_7_days == 10.5


def test_incomplete_window_is_unavailable_rather_than_partial():
    """Only 7 days of data exist, so a 30-day total would be misleading."""
    data = _data()
    assert data.last_30_days is None


def test_window_is_unavailable_when_a_day_is_missing_in_the_middle():
    archive = _build_archive()
    idx = archive["daily"]["time"].index("2026-06-13")
    archive["daily"]["precipitation_sum"][idx] = None
    data = build_rain_data(_build_forecast(), archive, NOW, 2, 0.1)
    assert data.last_7_days is None


def test_malformed_values_degrade_to_none_instead_of_raising():
    forecast = _build_forecast()
    idx = forecast["hourly"]["time"].index("2026-06-17T10:00")
    forecast["hourly"]["precipitation"][idx] = "not-a-number"
    archive = _build_archive()
    archive["daily"]["precipitation_sum"][0] = "junk"
    data = build_rain_data(forecast, archive, NOW, 2, 0.1)
    assert data.today_so_far == 0.5  # the 10:00 garbage is dropped, 11:00 remains
    assert data.last_7_days is None  # 2026-06-11 is now missing


def test_rain_soon_threshold_not_met():
    forecast = _build_forecast()
    idx = forecast["hourly"]["time"].index("2026-06-17T14:00")
    forecast["hourly"]["precipitation"][idx] = 0.0
    data = build_rain_data(forecast, _build_archive(), NOW, 2, 0.1)
    assert data.rain_soon is False
    assert data.minutes_until_rain is None


def test_midnight_stamp_belongs_to_the_previous_day():
    """The 00:00 stamp covers 23:00-00:00, so it is yesterday's rain."""
    forecast = _build_forecast()
    idx = forecast["hourly"]["time"].index("2026-06-17T00:00")
    forecast["hourly"]["precipitation"][idx] = 4.0
    data = build_rain_data(forecast, _build_archive(), NOW, 2, 0.1)
    assert data.today_so_far == 1.5


def test_today_is_zero_before_the_first_hour_has_elapsed():
    """Just after midnight no hour of the new day is complete yet."""
    forecast = _build_forecast()
    data = build_rain_data(
        forecast, _build_archive(), datetime(2026, 6, 18, 0, 30), 2, 0.1
    )
    assert data.today_so_far == 0.0
