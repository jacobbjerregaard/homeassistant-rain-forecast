"""Data update coordinator for the Rain Forecast & History integration."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import (
    CONF_FORECAST_DAYS,
    CONF_HISTORY_DAYS,
    CONF_RAIN_SOON_HOURS,
    CONF_RAIN_THRESHOLD,
    CONF_SCAN_MINUTES,
    DEFAULT_FORECAST_DAYS,
    DEFAULT_HISTORY_DAYS,
    DEFAULT_RAIN_SOON_HOURS,
    DEFAULT_RAIN_THRESHOLD,
    DEFAULT_SCAN_MINUTES,
    DOMAIN,
    RECENT_PAST_DAYS,
)
from .open_meteo import OpenMeteoClient, OpenMeteoError
from .parser import RainData, build_rain_data

_LOGGER = logging.getLogger(__name__)


def _local_now(forecast: dict) -> datetime:
    """Return "now" as a naive datetime in the *monitored location's* timezone.

    Open-Meteo is queried with ``timezone=auto``, so every timestamp it returns
    is local to the coordinates -- which is not necessarily HA's own timezone.
    Using HA's local time here would skew every window by the offset between the
    two (a Copenhagen instance watching New York would count six hours of
    forecast as rain that had already fallen), so we rebuild "now" from the
    ``utc_offset_seconds`` the response carries and drop the tzinfo to match.
    """
    offset = forecast.get("utc_offset_seconds")
    if isinstance(offset, (int, float)) and not isinstance(offset, bool):
        return (dt_util.utcnow() + timedelta(seconds=offset)).replace(tzinfo=None)
    # No offset in the payload: HA's local time is the best guess available, and
    # it is exactly right for the common case of monitoring your own location.
    _LOGGER.debug("No utc_offset_seconds in payload; falling back to HA local time")
    return dt_util.now().replace(tzinfo=None)


class RainForecastCoordinator(DataUpdateCoordinator[RainData]):
    """Fetch rainfall data from Open-Meteo and expose it to the entities."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialise the coordinator from a config entry."""
        self.entry = entry
        options = entry.options

        scan_minutes = options.get(CONF_SCAN_MINUTES, DEFAULT_SCAN_MINUTES)
        self.forecast_days = options.get(CONF_FORECAST_DAYS, DEFAULT_FORECAST_DAYS)
        self.history_days = options.get(CONF_HISTORY_DAYS, DEFAULT_HISTORY_DAYS)
        self.rain_soon_hours = options.get(
            CONF_RAIN_SOON_HOURS, DEFAULT_RAIN_SOON_HOURS
        )
        self.rain_threshold = options.get(
            CONF_RAIN_THRESHOLD, DEFAULT_RAIN_THRESHOLD
        )

        self.latitude = entry.data[CONF_LATITUDE]
        self.longitude = entry.data[CONF_LONGITUDE]

        session = async_get_clientsession(hass)
        self.client = OpenMeteoClient(session, self.latitude, self.longitude)

        # The archive (ERA5) only changes once a day, so it is cached and only
        # refreshed when the local date rolls over.
        self._archive: dict | None = None
        self._archive_day = None

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=scan_minutes),
        )

    async def _async_update_data(self) -> RainData:
        """Fetch the latest forecast and (once a day) the historical archive."""
        try:
            forecast = await self.client.async_get_forecast(
                self.forecast_days, RECENT_PAST_DAYS
            )
        except OpenMeteoError as err:
            raise UpdateFailed(f"Error fetching forecast: {err}") from err

        now = _local_now(forecast)
        today = now.date()

        if self._archive_day != today:
            start = (today - timedelta(days=self.history_days + 1)).isoformat()
            end = (today - timedelta(days=1)).isoformat()
            try:
                self._archive = await self.client.async_get_archive(start, end)
                self._archive_day = today
            except OpenMeteoError as err:
                # A stale or missing archive only affects the longer history
                # windows, so keep going with whatever we already have.
                _LOGGER.warning("Could not refresh rainfall archive: %s", err)

        return build_rain_data(
            forecast,
            self._archive,
            now,
            self.rain_soon_hours,
            self.rain_threshold,
        )
