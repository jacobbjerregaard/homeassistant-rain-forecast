"""Pure helpers that turn Open-Meteo payloads into the data the sensors expose.

These functions deliberately avoid any Home Assistant imports so the rainfall
logic can be unit-tested in isolation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class RainData:
    """Everything the sensors and binary sensor read from a coordinator refresh."""

    # Current conditions
    current_precipitation: float | None = None

    # Forecast
    forecast_today: float | None = None
    forecast_tomorrow: float | None = None
    probability_today: int | None = None
    probability_tomorrow: int | None = None
    next_hour: float | None = None
    next_24h: float | None = None

    # History
    today_so_far: float | None = None
    yesterday: float | None = None
    last_7_days: float | None = None
    last_30_days: float | None = None

    # "Rain soon" detection
    rain_soon: bool = False
    minutes_until_rain: int | None = None
    rain_soon_amount: float | None = None

    # Raw-ish daily forecast, surfaced as an attribute for templating/charts.
    daily_forecast: list[dict[str, Any]] = field(default_factory=list)


def _get(values: list[Any], index: int) -> Any:
    """Return ``values[index]`` or ``None`` when out of range."""
    if 0 <= index < len(values):
        return values[index]
    return None


def _round(value: float | None, ndigits: int = 2) -> float | None:
    """Round, tolerating ``None``."""
    return round(value, ndigits) if value is not None else None


def _as_int(value: Any) -> int | None:
    """Coerce to int, tolerating ``None``/garbage."""
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _window_sum(
    actual: dict[str, float], end: datetime, days: int
) -> float | None:
    """Sum the rainfall for the ``days`` ending on ``end`` (inclusive)."""
    total = 0.0
    found = False
    for offset in range(days):
        key = (end.date() - timedelta(days=offset)).isoformat()
        value = actual.get(key)
        if value is not None:
            total += value
            found = True
    return total if found else None


def build_rain_data(
    forecast: dict[str, Any],
    archive: dict[str, Any] | None,
    now: datetime,
    rain_soon_hours: int,
    rain_threshold: float,
) -> RainData:
    """Build a :class:`RainData` from the Open-Meteo forecast and archive payloads.

    ``now`` is expected to be a naive ``datetime`` in the location's local time,
    matching the naive timestamps Open-Meteo returns with ``timezone=auto``.
    """
    data = RainData()

    today = now.date()
    today_str = today.isoformat()
    tomorrow_str = (today + timedelta(days=1)).isoformat()
    yesterday_str = (today - timedelta(days=1)).isoformat()

    # --- Daily forecast block (spans past_days .. forecast_days) ----------
    daily = forecast.get("daily") or {}
    d_dates: list[str] = daily.get("time") or []
    d_psum = daily.get("precipitation_sum") or []
    d_prob = daily.get("precipitation_probability_max") or []
    d_rain = daily.get("rain_sum") or []
    d_hours = daily.get("precipitation_hours") or []

    daily_by_date: dict[str, dict[str, Any]] = {}
    for i, date_str in enumerate(d_dates):
        daily_by_date[date_str] = {
            "precipitation_sum": _get(d_psum, i),
            "precipitation_probability_max": _get(d_prob, i),
            "rain_sum": _get(d_rain, i),
            "precipitation_hours": _get(d_hours, i),
        }

    if today_str in daily_by_date:
        data.forecast_today = _round(daily_by_date[today_str]["precipitation_sum"])
        data.probability_today = _as_int(
            daily_by_date[today_str]["precipitation_probability_max"]
        )
    if tomorrow_str in daily_by_date:
        data.forecast_tomorrow = _round(
            daily_by_date[tomorrow_str]["precipitation_sum"]
        )
        data.probability_tomorrow = _as_int(
            daily_by_date[tomorrow_str]["precipitation_probability_max"]
        )

    data.daily_forecast = [
        {"date": date_str, **daily_by_date[date_str]}
        for date_str in d_dates
        if date_str >= today_str
    ]

    # --- Current conditions ----------------------------------------------
    current = forecast.get("current") or {}
    data.current_precipitation = _round(current.get("precipitation"))

    # --- Hourly walk: next hour, next 24h, today-so-far, rain-soon -------
    hourly = forecast.get("hourly") or {}
    h_times: list[str] = hourly.get("time") or []
    h_precip = hourly.get("precipitation") or []

    next_hour: float | None = None
    next_24h = 0.0
    has_24h = False
    today_so_far = 0.0
    has_today = False
    minutes_until: int | None = None
    soon_amount: float | None = None

    horizon = now + timedelta(hours=24)
    soon_limit = now + timedelta(hours=rain_soon_hours)

    for i, time_str in enumerate(h_times):
        try:
            moment = datetime.fromisoformat(time_str)
        except ValueError:
            continue
        precip = _get(h_precip, i) or 0.0

        if moment.date() == today and moment <= now:
            today_so_far += precip
            has_today = True

        if moment >= now:
            if next_hour is None:
                next_hour = precip
            if moment < horizon:
                next_24h += precip
                has_24h = True
            if (
                minutes_until is None
                and moment <= soon_limit
                and precip >= rain_threshold
            ):
                minutes_until = max(0, int((moment - now).total_seconds() // 60))
                soon_amount = precip

    data.next_hour = _round(next_hour)
    data.next_24h = _round(next_24h) if has_24h else None
    data.today_so_far = _round(today_so_far) if has_today else None
    data.rain_soon = minutes_until is not None
    data.minutes_until_rain = minutes_until
    data.rain_soon_amount = _round(soon_amount)

    # --- History: merge archive + recent forecast + today-so-far ---------
    actual: dict[str, float] = {}

    if archive:
        a_daily = archive.get("daily") or {}
        a_dates: list[str] = a_daily.get("time") or []
        a_psum = a_daily.get("precipitation_sum") or []
        for i, date_str in enumerate(a_dates):
            value = _get(a_psum, i)
            if value is not None:
                actual[date_str] = value

    # The live endpoint's past_days data is fresher than the archive, so let it
    # win for any overlapping recent dates.
    for date_str, values in daily_by_date.items():
        if date_str < today_str and values["precipitation_sum"] is not None:
            actual[date_str] = values["precipitation_sum"]

    if has_today:
        actual[today_str] = today_so_far

    data.yesterday = _round(actual.get(yesterday_str))
    data.last_7_days = _round(_window_sum(actual, now, 7))
    data.last_30_days = _round(_window_sum(actual, now, 30))

    return data
