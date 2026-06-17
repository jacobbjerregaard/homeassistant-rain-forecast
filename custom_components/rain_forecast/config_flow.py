"""Config and options flow for the Rain Forecast & History integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv

from .const import (
    CONF_FORECAST_DAYS,
    CONF_HISTORY_DAYS,
    CONF_RAIN_SOON_HOURS,
    CONF_RAIN_THRESHOLD,
    CONF_SCAN_MINUTES,
    DEFAULT_FORECAST_DAYS,
    DEFAULT_HISTORY_DAYS,
    DEFAULT_NAME,
    DEFAULT_RAIN_SOON_HOURS,
    DEFAULT_RAIN_THRESHOLD,
    DEFAULT_SCAN_MINUTES,
    DOMAIN,
)


class RainForecastConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the initial setup for a rain location."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a name and the location to monitor."""
        errors: dict[str, str] = {}

        if user_input is not None:
            latitude = user_input[CONF_LATITUDE]
            longitude = user_input[CONF_LONGITUDE]
            await self.async_set_unique_id(f"{latitude}-{longitude}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=user_input[CONF_NAME], data=user_input
            )

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                vol.Required(
                    CONF_LATITUDE, default=self.hass.config.latitude
                ): cv.latitude,
                vol.Required(
                    CONF_LONGITUDE, default=self.hass.config.longitude
                ): cv.longitude,
            }
        )
        return self.async_show_form(
            step_id="user", data_schema=schema, errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> RainForecastOptionsFlow:
        """Return the options flow handler."""
        return RainForecastOptionsFlow(config_entry)


class RainForecastOptionsFlow(OptionsFlow):
    """Handle tuning options after setup."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        """Store the entry being configured."""
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the integration options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self._entry.options
        schema = vol.Schema(
            {
                vol.Required(
                    CONF_SCAN_MINUTES,
                    default=options.get(CONF_SCAN_MINUTES, DEFAULT_SCAN_MINUTES),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=360)),
                vol.Required(
                    CONF_FORECAST_DAYS,
                    default=options.get(CONF_FORECAST_DAYS, DEFAULT_FORECAST_DAYS),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=16)),
                vol.Required(
                    CONF_HISTORY_DAYS,
                    default=options.get(CONF_HISTORY_DAYS, DEFAULT_HISTORY_DAYS),
                ): vol.All(vol.Coerce(int), vol.Range(min=7, max=92)),
                vol.Required(
                    CONF_RAIN_SOON_HOURS,
                    default=options.get(
                        CONF_RAIN_SOON_HOURS, DEFAULT_RAIN_SOON_HOURS
                    ),
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=12)),
                vol.Required(
                    CONF_RAIN_THRESHOLD,
                    default=options.get(
                        CONF_RAIN_THRESHOLD, DEFAULT_RAIN_THRESHOLD
                    ),
                ): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=10.0)),
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
