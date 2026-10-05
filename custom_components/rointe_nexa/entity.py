"""Base entity for Rointe Nexa integration."""
from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import RointeDataUpdateCoordinator
from .rointe_nexa import NexaDevice


class RointeEntity(CoordinatorEntity[RointeDataUpdateCoordinator]):
    """Base representation of a Rointe Nexa entity."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RointeDataUpdateCoordinator,
        device: NexaDevice,
        key: str,
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        self.device = device
        self.serial = device.serial_number
        self._attr_unique_id = f"{device.serial_number}_{key}"

        # Fetch initial firmware info if available
        firmware = self.device_state.get("firmware", {})
        sw_version = str(firmware.get("firmware_version")) if firmware.get("firmware_version") else None
        hw_version = str(firmware.get("hardware_version")) if firmware.get("hardware_version") else None

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.serial_number)},
            name=device.name,
            manufacturer="Rointe",
            model="Nexa Radiator",
            suggested_area=device.zone_name,
            sw_version=sw_version,
            hw_version=hw_version,
        )

    @property
    def device_state(self) -> dict[str, Any]:
        """Return the device state dictionary."""
        return self.coordinator.data.get(self.serial, {})

    @property
    def device_data(self) -> dict[str, Any]:
        """Return the internal telemetry data dictionary."""
        return self.device_state.get("data", {})

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not super().available:
            return False
        # If device is alive flag is present and False, mark unavailable
        return self.device_data.get("is_alive", True)
