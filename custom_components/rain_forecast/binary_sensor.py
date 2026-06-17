"""Binary sensor that flags imminent rain for the integration."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import ATTRIBUTION, DOMAIN, MANUFACTURER, MODEL
from .coordinator import RainForecastCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the rain-soon binary sensor from a config entry."""
    coordinator: RainForecastCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([RainSoonBinarySensor(coordinator, entry)])


class RainSoonBinarySensor(
    CoordinatorEntity[RainForecastCoordinator], BinarySensorEntity
):
    """On when rain is expected within the configured look-ahead window."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _attr_translation_key = "rain_soon"
    _attr_device_class = BinarySensorDeviceClass.MOISTURE
    _attr_icon = "mdi:weather-rainy"

    def __init__(
        self, coordinator: RainForecastCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialise the binary sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_rain_soon"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
            configuration_url="https://open-meteo.com/",
        )

    @property
    def is_on(self) -> bool | None:
        """Return True when rain is imminent."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.rain_soon

    @property
    def extra_state_attributes(self) -> dict | None:
        """Expose how soon and how much rain is expected."""
        if self.coordinator.data is None:
            return None
        return {
            "minutes_until_rain": self.coordinator.data.minutes_until_rain,
            "expected_amount": self.coordinator.data.rain_soon_amount,
            "look_ahead_hours": self.coordinator.rain_soon_hours,
        }
