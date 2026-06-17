"""Constants for the Rain Forecast & History integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "rain_forecast"

# Configuration / options keys
CONF_FORECAST_DAYS: Final = "forecast_days"
CONF_HISTORY_DAYS: Final = "history_days"
CONF_SCAN_MINUTES: Final = "scan_minutes"
CONF_RAIN_SOON_HOURS: Final = "rain_soon_hours"
CONF_RAIN_THRESHOLD: Final = "rain_threshold"

# Defaults
DEFAULT_NAME: Final = "Rain"
DEFAULT_FORECAST_DAYS: Final = 7
DEFAULT_HISTORY_DAYS: Final = 30
DEFAULT_SCAN_MINUTES: Final = 30
DEFAULT_RAIN_SOON_HOURS: Final = 2
DEFAULT_RAIN_THRESHOLD: Final = 0.1  # mm in an hour counts as "rain soon"

# Number of past days we ask the live forecast endpoint for. The archive API
# fills in anything older than this when building the longer history windows.
RECENT_PAST_DAYS: Final = 7

# Open-Meteo endpoints (free, no API key required).
FORECAST_URL: Final = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL: Final = "https://archive-api.open-meteo.com/v1/archive"

ATTRIBUTION: Final = "Weather data by Open-Meteo.com"
MANUFACTURER: Final = "Open-Meteo"
MODEL: Final = "Rain Forecast & History"
