"""Number entities for Rointe Nexa preset temperature settings."""
from __future__ import annotations

import logging

from homeassistant.components.number import NumberDeviceClass, NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, PRESET_COMFORT, PRESET_ECO, PRESET_ICE
from .coordinator import RointeDataUpdateCoordinator
from .entity import RointeEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Rointe Nexa number entities."""
    coordinator: RointeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[NumberEntity] = []
    for device in coordinator.devices:
        entities.extend(
            [
                RointeComfortTempNumber(coordinator, device),
                RointeEcoTempNumber(coordinator, device),
                RointeIceTempNumber(coordinator, device),
            ]
        )

    async_add_entities(entities)


class RointeComfortTempNumber(RointeEntity, NumberEntity):
    """Number entity to configure the Comfort preset temperature."""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = 7.0
    _attr_native_max_value = 30.0
    _attr_native_step = 0.5
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "comfort_temperature"

    def __init__(self, coordinator: RointeDataUpdateCoordinator, device) -> None:
        """Initialize number entity."""
        super().__init__(coordinator, device, "comfort_temp")
        self._attr_name = "Comfort Temperature"

    @property
    def native_value(self) -> float | None:
        """Return the current comfort temperature setting."""
        val = self.device_data.get("comfort")
        try:
            return float(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Update comfort temperature setting."""
        resp = await self.hass.async_add_executor_job(
            self.coordinator.api.set_preset_temperature,
            self.serial,
            PRESET_COMFORT,
            value,
        )
        if resp.success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error(
                "Failed to set comfort temperature for %s: %s",
                self.name,
                resp.error_message,
            )


class RointeEcoTempNumber(RointeEntity, NumberEntity):
    """Number entity to configure the Eco preset temperature."""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = 7.0
    _attr_native_max_value = 30.0
    _attr_native_step = 0.5
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "eco_temperature"

    def __init__(self, coordinator: RointeDataUpdateCoordinator, device) -> None:
        """Initialize number entity."""
        super().__init__(coordinator, device, "eco_temp")
        self._attr_name = "Eco Temperature"

    @property
    def native_value(self) -> float | None:
        """Return the current eco temperature setting."""
        val = self.device_data.get("eco")
        try:
            return float(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Update eco temperature setting."""
        resp = await self.hass.async_add_executor_job(
            self.coordinator.api.set_preset_temperature,
            self.serial,
            PRESET_ECO,
            value,
        )
        if resp.success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error(
                "Failed to set eco temperature for %s: %s",
                self.name,
                resp.error_message,
            )


class RointeIceTempNumber(RointeEntity, NumberEntity):
    """Number entity to configure the Anti-frost (Ice) preset temperature."""

    _attr_device_class = NumberDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_native_min_value = 7.0
    _attr_native_max_value = 15.0
    _attr_native_step = 0.5
    _attr_mode = NumberMode.BOX
    _attr_entity_category = EntityCategory.CONFIG
    _attr_translation_key = "ice_temperature"

    def __init__(self, coordinator: RointeDataUpdateCoordinator, device) -> None:
        """Initialize number entity."""
        super().__init__(coordinator, device, "ice_temp")
        self._attr_name = "Anti-frost Temperature"

    @property
    def native_value(self) -> float | None:
        """Return the current ice temperature setting."""
        val = self.device_data.get("ice")
        try:
            return float(val) if val is not None else None
        except (ValueError, TypeError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Update ice temperature setting."""
        resp = await self.hass.async_add_executor_job(
            self.coordinator.api.set_preset_temperature,
            self.serial,
            PRESET_ICE,
            value,
        )
        if resp.success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error(
                "Failed to set anti-frost temperature for %s: %s",
                self.name,
                resp.error_message,
            )
