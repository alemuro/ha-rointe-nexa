"""Binary sensors for Rointe Nexa."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import RointeDataUpdateCoordinator
from .entity import RointeEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Rointe Nexa binary sensors."""
    coordinator: RointeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[BinarySensorEntity] = []
    for device in coordinator.devices:
        entities.extend(
            [
                RointeHeatingBinarySensor(coordinator, device),
                RointeWindowBinarySensor(coordinator, device),
                RointeConnectivityBinarySensor(coordinator, device),
            ]
        )

    async_add_entities(entities)


class RointeHeatingBinarySensor(RointeEntity, BinarySensorEntity):
    """Binary sensor indicating if radiator is actively heating."""

    _attr_device_class = BinarySensorDeviceClass.HEAT
    _attr_translation_key = "heating"

    def __init__(self, coordinator: RointeDataUpdateCoordinator, device) -> None:
        """Initialize binary sensor."""
        super().__init__(coordinator, device, "heating")
        self._attr_name = "Heating"

    @property
    def is_on(self) -> bool:
        """Return True if heating."""
        power = self.device_data.get("power")
        status = self.device_data.get("status")
        warming = self.device_data.get("status_warming")

        if power == 1 or status == "off":
            return False
        return warming == 2


class RointeWindowBinarySensor(RointeEntity, BinarySensorEntity):
    """Binary sensor indicating if an open window has been detected."""

    _attr_device_class = BinarySensorDeviceClass.WINDOW
    _attr_translation_key = "window_open"

    def __init__(self, coordinator: RointeDataUpdateCoordinator, device) -> None:
        """Initialize binary sensor."""
        super().__init__(coordinator, device, "window_open")
        self._attr_name = "Window Open"

    @property
    def is_on(self) -> bool:
        """Return True if open window detected."""
        return bool(self.device_data.get("windows_open_status", False))


class RointeConnectivityBinarySensor(RointeEntity, BinarySensorEntity):
    """Binary sensor indicating device connectivity status."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_translation_key = "connectivity"

    def __init__(self, coordinator: RointeDataUpdateCoordinator, device) -> None:
        """Initialize binary sensor."""
        super().__init__(coordinator, device, "connectivity")
        self._attr_name = "Connectivity"

    @property
    def is_on(self) -> bool:
        """Return True if device is online and responsive."""
        return bool(self.device_data.get("is_alive", True))
