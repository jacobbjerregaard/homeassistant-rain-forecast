"""Thin async client for the Open-Meteo forecast and archive APIs."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import aiohttp

from .const import ARCHIVE_URL, FORECAST_URL

_LOGGER = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=30)

# Variables requested from each endpoint.
_HOURLY = "precipitation,precipitation_probability,rain,showers"
_DAILY = (
    "precipitation_sum,rain_sum,showers_sum,"
    "precipitation_probability_max,precipitation_hours"
)
_CURRENT = "precipitation,rain,showers,weather_code"


class OpenMeteoError(Exception):
    """Raised when an Open-Meteo request fails."""


class OpenMeteoClient:
    """Fetch precipitation data from Open-Meteo for a single location."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        latitude: float,
        longitude: float,
    ) -> None:
        """Initialise the client."""
        self._session = session
        self._latitude = latitude
        self._longitude = longitude

    async def async_get_forecast(
        self, forecast_days: int, past_days: int
    ) -> dict[str, Any]:
        """Return current conditions plus hourly and daily forecast/recent data."""
        params = {
            "latitude": self._latitude,
            "longitude": self._longitude,
            "timezone": "auto",
            "forecast_days": forecast_days,
            "past_days": past_days,
            "current": _CURRENT,
            "hourly": _HOURLY,
            "daily": _DAILY,
        }
        return await self._get(FORECAST_URL, params)

    async def async_get_archive(self, start_date: str, end_date: str) -> dict[str, Any]:
        """Return historical daily rainfall totals from the archive (ERA5)."""
        params = {
            "latitude": self._latitude,
            "longitude": self._longitude,
            "timezone": "auto",
            "start_date": start_date,
            "end_date": end_date,
            "daily": "precipitation_sum,rain_sum",
        }
        return await self._get(ARCHIVE_URL, params)

    async def _get(self, url: str, params: dict[str, Any]) -> dict[str, Any]:
        """Perform the request and return the decoded JSON body."""
        try:
            async with self._session.get(
                url, params=params, timeout=_TIMEOUT
            ) as response:
                body: dict[str, Any] = await response.json()
                if response.status != 200:
                    reason = body.get("reason") if isinstance(body, dict) else None
                    raise OpenMeteoError(
                        f"Open-Meteo returned HTTP {response.status}"
                        + (f": {reason}" if reason else "")
                    )
                if isinstance(body, dict) and body.get("error"):
                    raise OpenMeteoError(
                        f"Open-Meteo error: {body.get('reason', 'unknown')}"
                    )
                return body
        except asyncio.TimeoutError as err:
            raise OpenMeteoError("Timeout talking to Open-Meteo") from err
        except aiohttp.ClientError as err:
            raise OpenMeteoError(f"Connection error talking to Open-Meteo: {err}") from err
