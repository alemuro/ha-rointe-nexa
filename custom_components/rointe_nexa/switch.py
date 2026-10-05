"""Switches for Rointe Nexa."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import RointeDataUpdateCoordinator
from .entity import RointeEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Rointe Nexa switches."""
    coordinator: RointeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SwitchEntity] = []
    for device in coordinator.devices:
        entities.extend(
            [
                RointeKeypadLockSwitch(coordinator, device),
                RointeWindowDetectionSwitch(coordinator, device),
            ]
        )

    async_add_entities(entities)


class RointeKeypadLockSwitch(RointeEntity, SwitchEntity):
    """Switch to lock or unlock the physical keypad on the radiator."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:lock"
    _attr_translation_key = "keypad_lock"

    def __init__(self, coordinator: RointeDataUpdateCoordinator, device) -> None:
        """Initialize switch."""
        super().__init__(coordinator, device, "keypad_lock")
        self._attr_name = "Keypad Lock"

    @property
    def is_on(self) -> bool:
        """Return True if keypad is locked."""
        return bool(self.device_data.get("block_local", False))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn switch on (lock keypad)."""
        resp = await self.hass.async_add_executor_job(
            self.coordinator.api.set_keypad_lock, self.serial, True
        )
        if resp.success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to lock keypad for %s: %s", self.name, resp.error_message)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn switch off (unlock keypad)."""
        resp = await self.hass.async_add_executor_job(
            self.coordinator.api.set_keypad_lock, self.serial, False
        )
        if resp.success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to unlock keypad for %s: %s", self.name, resp.error_message)


class RointeWindowDetectionSwitch(RointeEntity, SwitchEntity):
    """Switch to enable or disable open window detection."""

    _attr_device_class = SwitchDeviceClass.SWITCH
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:window-open-variant"
    _attr_translation_key = "window_detection"

    def __init__(self, coordinator: RointeDataUpdateCoordinator, device) -> None:
        """Initialize switch."""
        super().__init__(coordinator, device, "window_detection")
        self._attr_name = "Open Window Detection"

    @property
    def is_on(self) -> bool:
        """Return True if open window detection is enabled."""
        return bool(self.device_data.get("windows_open_mode", False))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn switch on (enable window detection)."""
        resp = await self.hass.async_add_executor_job(
            self.coordinator.api.set_open_window_detection, self.serial, True
        )
        if resp.success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error(
                "Failed to enable open window detection for %s: %s",
                self.name,
                resp.error_message,
            )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn switch off (disable window detection)."""
        resp = await self.hass.async_add_executor_job(
            self.coordinator.api.set_open_window_detection, self.serial, False
        )
        if resp.success:
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error(
                "Failed to disable open window detection for %s: %s",
                self.name,
                resp.error_message,
            )
