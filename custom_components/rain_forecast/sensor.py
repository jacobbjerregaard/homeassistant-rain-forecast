"""Sensor entities for the Rain Forecast & History integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from homeassistant.components.sensor import (
    RestoreSensor,
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfPrecipitationDepth, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import StateType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from .accumulator import RainAccumulator
from .const import ATTRIBUTION, DOMAIN, MANUFACTURER, MODEL
from .coordinator import RainForecastCoordinator
from .parser import RainData

_MM = UnitOfPrecipitationDepth.MILLIMETERS


@dataclass(frozen=True, kw_only=True)
class RainSensorEntityDescription(SensorEntityDescription):
    """Describes a Rain Forecast sensor and how to read its value."""

    value_fn: Callable[[RainData], StateType]
    #: Set for TOTAL sensors whose accumulation restarts at local midnight.
    resets_daily: bool = False


SENSORS: tuple[RainSensorEntityDescription, ...] = (
    # --- Current ---------------------------------------------------------
    RainSensorEntityDescription(
        key="current_precipitation",
        translation_key="current_precipitation",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=_MM,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-rainy",
        value_fn=lambda d: d.current_precipitation,
    ),
    # --- Forecast --------------------------------------------------------
    RainSensorEntityDescription(
        key="forecast_today",
        translation_key="forecast_today",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=_MM,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-pouring",
        value_fn=lambda d: d.forecast_today,
    ),
    RainSensorEntityDescription(
        key="forecast_tomorrow",
        translation_key="forecast_tomorrow",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=_MM,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-pouring",
        value_fn=lambda d: d.forecast_tomorrow,
    ),
    RainSensorEntityDescription(
        key="probability_today",
        translation_key="probability_today",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-rainy",
        value_fn=lambda d: d.probability_today,
    ),
    RainSensorEntityDescription(
        key="probability_tomorrow",
        translation_key="probability_tomorrow",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-rainy",
        value_fn=lambda d: d.probability_tomorrow,
    ),
    RainSensorEntityDescription(
        key="next_hour",
        translation_key="next_hour",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=_MM,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-rainy",
        value_fn=lambda d: d.next_hour,
    ),
    RainSensorEntityDescription(
        key="next_24h",
        translation_key="next_24h",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=_MM,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-pouring",
        value_fn=lambda d: d.next_24h,
    ),
    RainSensorEntityDescription(
        key="minutes_until_rain",
        translation_key="minutes_until_rain",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.MINUTES,
        icon="mdi:timer-sand",
        value_fn=lambda d: d.minutes_until_rain,
    ),
    # --- History ---------------------------------------------------------
    RainSensorEntityDescription(
        key="today_so_far",
        translation_key="today_so_far",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=_MM,
        # Deliberately TOTAL rather than TOTAL_INCREASING: this value is
        # re-derived from Open-Meteo's hourly series on every poll, and the
        # model revises hours that have already elapsed, so it can legitimately
        # fall. TOTAL_INCREASING would read each revision as a counter reset and
        # inflate the long-term statistics. See issue #1.
        state_class=SensorStateClass.TOTAL,
        resets_daily=True,
        icon="mdi:weather-rainy",
        value_fn=lambda d: d.today_so_far,
    ),
    RainSensorEntityDescription(
        key="yesterday",
        translation_key="yesterday",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=_MM,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-rainy",
        value_fn=lambda d: d.yesterday,
    ),
    RainSensorEntityDescription(
        key="last_7_days",
        translation_key="last_7_days",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=_MM,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-pouring",
        value_fn=lambda d: d.last_7_days,
    ),
    RainSensorEntityDescription(
        key="last_30_days",
        translation_key="last_30_days",
        device_class=SensorDeviceClass.PRECIPITATION,
        native_unit_of_measurement=_MM,
        state_class=SensorStateClass.MEASUREMENT,
        icon="mdi:weather-pouring",
        value_fn=lambda d: d.last_30_days,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the rain sensors from a config entry."""
    coordinator: RainForecastCoordinator = hass.data[DOMAIN][entry.entry_id]
    entities: list[SensorEntity] = [
        RainSensor(coordinator, entry, description) for description in SENSORS
    ]
    entities.append(RainAccumulatedSensor(coordinator, entry))
    async_add_entities(entities)


def _device_info(entry: ConfigEntry) -> DeviceInfo:
    """Group every entity under a single device for this location."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer=MANUFACTURER,
        model=MODEL,
        configuration_url="https://open-meteo.com/",
    )


class RainSensor(CoordinatorEntity[RainForecastCoordinator], SensorEntity):
    """A sensor whose value is read straight from the coordinator data."""

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    entity_description: RainSensorEntityDescription

    def __init__(
        self,
        coordinator: RainForecastCoordinator,
        entry: ConfigEntry,
        description: RainSensorEntityDescription,
    ) -> None:
        """Initialise the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_device_info = _device_info(entry)

    @property
    def native_value(self) -> StateType:
        """Return the current value of the sensor."""
        if self.coordinator.data is None:
            return None
        return self.entity_description.value_fn(self.coordinator.data)

    @property
    def last_reset(self) -> datetime | None:
        """Return local midnight for sensors that start over each day."""
        if not self.entity_description.resets_daily:
            return None
        return dt_util.start_of_local_day()

    @property
    def extra_state_attributes(self) -> dict | None:
        """Expose the daily forecast on the today sensor for charts/templates."""
        if (
            self.entity_description.key == "forecast_today"
            and self.coordinator.data is not None
        ):
            return {"daily_forecast": self.coordinator.data.daily_forecast}
        return None


class RainAccumulatedSensor(
    CoordinatorEntity[RainForecastCoordinator], RestoreSensor
):
    """A lifetime rainfall total accumulated locally and restored across restarts.

    This is intentionally independent of the API history windows: it keeps
    counting up even if the archive is unavailable, giving a resilient
    "total rain since installed" figure.
    """

    _attr_has_entity_name = True
    _attr_attribution = ATTRIBUTION
    _attr_translation_key = "accumulated"
    _attr_icon = "mdi:cup-water"
    _attr_device_class = SensorDeviceClass.PRECIPITATION
    _attr_native_unit_of_measurement = _MM
    _attr_state_class = SensorStateClass.TOTAL_INCREASING
    _attr_suggested_display_precision = 1

    def __init__(
        self, coordinator: RainForecastCoordinator, entry: ConfigEntry
    ) -> None:
        """Initialise the accumulated sensor."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_accumulated"
        self._attr_device_info = _device_info(entry)
        self._accumulator = RainAccumulator()

    async def async_added_to_hass(self) -> None:
        """Restore the running total and seed the baseline."""
        await super().async_added_to_hass()
        total = 0.0
        last = await self.async_get_last_sensor_data()
        if last is not None and last.native_value is not None:
            try:
                total = float(last.native_value)
            except (TypeError, ValueError):
                total = 0.0
        # Re-baseline after a restart so the first refresh doesn't double count.
        self._accumulator.reset_baseline(total)
        self._attr_native_value = round(total, 2)
        self._accumulate()

    @callback
    def _handle_coordinator_update(self) -> None:
        """Accumulate on each coordinator refresh."""
        self._accumulate()
        self.async_write_ha_state()

    def _accumulate(self) -> None:
        """Fold today's rainfall-so-far into the running total."""
        data = self.coordinator.data
        if data is None:
            return
        # The first entry of the daily forecast is always "today" in local time,
        # so we use it to detect a day rollover without recomputing the date here.
        date = data.daily_forecast[0]["date"] if data.daily_forecast else None
        self._attr_native_value = round(
            self._accumulator.add(data.today_so_far, date), 2
        )
