"""Support for Rointe Nexa heaters."""
from __future__ import annotations

import asyncio
from datetime import datetime
import logging
from typing import Any



from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
    PRESET_AWAY,
    PRESET_COMFORT,
    PRESET_ECO,
    PRESET_NONE,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, PRESET_ICE
from .coordinator import RointeDataUpdateCoordinator
from .entity import RointeEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Rointe Nexa climate platform."""
    coordinator: RointeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities = [
        RointeNexaClimate(coordinator, device)
        for device in coordinator.devices
    ]

    async_add_entities(entities)


class RointeNexaClimate(RointeEntity, ClimateEntity):
    """Representation of a Rointe Nexa Climate entity."""

    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 7.0
    _attr_max_temp = 30.0
    _attr_target_temperature_step = 0.5
    _attr_hvac_modes = [HVACMode.HEAT, HVACMode.AUTO, HVACMode.OFF]
    _attr_preset_modes = [PRESET_NONE, PRESET_COMFORT, PRESET_ECO, PRESET_AWAY]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.PRESET_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator: RointeDataUpdateCoordinator, device) -> None:
        """Initialize the climate entity."""
        super().__init__(coordinator, device, "climate")

    @property
    def current_temperature(self) -> float | None:
        """Return the current temperature."""
        temp = self.device_data.get("temp_probe")
        try:
            return float(temp) if temp is not None else None
        except (ValueError, TypeError):
            return None

    def _get_active_preset(self) -> str | None:
        """Return the active preset based on status or schedule."""
        status = str(self.device_data.get("status", "")).lower()
        if status in ("comfort", "eco", "ice", "away"):
            return status

        # If in auto mode and status is none/empty, look up schedule
        mode = self.device_data.get("mode")
        if mode == 1:
            sched = self.device_data.get("schedule")
            if isinstance(sched, (list, dict)):
                now = datetime.now()
                weekday = now.weekday()
                hour = now.hour
                day_str = (
                    sched[weekday]
                    if isinstance(sched, list) and len(sched) > weekday
                    else sched.get(str(weekday), "")
                    if isinstance(sched, dict)
                    else ""
                )
                if isinstance(day_str, str) and len(day_str) > hour:
                    code = day_str[hour].upper()
                    if code == "C":
                        return "comfort"
                    elif code == "E":
                        return "eco"
                    elif code in ("I", "A", "O", "0"):
                        return "ice"
        return None

    @property
    def target_temperature(self) -> float | None:
        """Return the temperature we try to reach."""
        # When in Auto mode or when a preset is active, use the preset's temperature
        preset = self._get_active_preset()
        if preset == "comfort":
            if (val := self.device_data.get("comfort")) is not None:
                return float(val)
        elif preset == "eco":
            if (val := self.device_data.get("eco")) is not None:
                return float(val)
        elif preset in ("ice", "away"):
            if (val := self.device_data.get("ice")) is not None:
                return float(val)

        # In manual mode without preset, return the manual setpoint 'temp'
        temp = self.device_data.get("temp")
        try:
            return float(temp) if temp is not None else None
        except (ValueError, TypeError):
            return None

    @property
    def hvac_mode(self) -> HVACMode:
        """Return current operation mode."""
        power = self.device_data.get("power")
        status = self.device_data.get("status")
        mode = self.device_data.get("mode")

        if power == 1 or status == "off":
            return HVACMode.OFF
        if mode == 1:
            return HVACMode.AUTO
        return HVACMode.HEAT

    @property
    def hvac_action(self) -> HVACAction:
        """Return current HVAC action."""
        if self.hvac_mode == HVACMode.OFF:
            return HVACAction.OFF
        warming = self.device_data.get("status_warming")
        if warming == 2:
            return HVACAction.HEATING
        return HVACAction.IDLE

    @property
    def preset_mode(self) -> str:
        """Return the current preset mode."""
        preset = self._get_active_preset()
        if preset == "comfort":
            return PRESET_COMFORT
        if preset == "eco":
            return PRESET_ECO
        if preset in ("ice", "away"):
            return PRESET_AWAY
        return PRESET_NONE


    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return device specific state attributes."""
        attrs: dict[str, Any] = {}
        if (surface_temp := self.device_data.get("temp_surface")) is not None:
            attrs["surface_temperature"] = surface_temp
        if (comfort_temp := self.device_data.get("comfort")) is not None:
            attrs["preset_comfort_temperature"] = comfort_temp
        if (eco_temp := self.device_data.get("eco")) is not None:
            attrs["preset_eco_temperature"] = eco_temp
        if (ice_temp := self.device_data.get("ice")) is not None:
            attrs["preset_ice_temperature"] = ice_temp
        if (locked := self.device_data.get("block_local")) is not None:
            attrs["keypad_locked"] = locked
        if (win_mode := self.device_data.get("windows_open_mode")) is not None:
            attrs["window_detection_mode"] = win_mode
        if (win_status := self.device_data.get("windows_open_status")) is not None:
            attrs["window_open_detected"] = win_status
        return attrs

    async def async_set_temperature(self, **kwargs: Any) -> None:
        """Set new target temperature."""
        if (temp := kwargs.get(ATTR_TEMPERATURE)) is None:
            return

        active_preset = self._get_active_preset()

        if self.hvac_mode == HVACMode.AUTO:
            # If in ice/away preset in schedule, ignore changes to protect anti-frost setting
            if active_preset in ("ice", "away"):
                _LOGGER.info(
                    "Ignoring temperature change for %s: device is in %s mode (schedule)",
                    self.name,
                    active_preset,
                )
                self.async_write_ha_state()
                return

            # If in comfort or eco, update the respective preset temperature
            if active_preset in ("comfort", "eco"):
                resp = await self.hass.async_add_executor_job(
                    self.coordinator.api.set_preset_temperature,
                    self.serial,
                    active_preset,
                    temp,
                )
                if resp.success:
                    if dev_data := self.coordinator.data.get(self.serial, {}).get("data"):
                        dev_data[active_preset] = temp
                    self.async_write_ha_state()
                    await asyncio.sleep(0.5)
                    await self.coordinator.async_request_refresh()
                else:
                    _LOGGER.error(
                        "Failed to set %s preset temperature for %s: %s",
                        active_preset,
                        self.name,
                        resp.error_message,
                    )
                return

        # Default behavior in HEAT / manual mode
        resp = await self.hass.async_add_executor_job(
            self.coordinator.api.set_temperature, self.serial, temp
        )
        if resp.success:
            if dev_data := self.coordinator.data.get(self.serial, {}).get("data"):
                dev_data["temp"] = temp
                dev_data["power"] = 2
                dev_data["status"] = "none"
                dev_data["mode"] = 0
            self.async_write_ha_state()
            await asyncio.sleep(0.5)
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set temperature for %s: %s", self.name, resp.error_message)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set new target hvac mode."""
        resp = await self.hass.async_add_executor_job(
            self.coordinator.api.set_hvac_mode, self.serial, hvac_mode.value
        )
        if resp.success:
            if dev_data := self.coordinator.data.get(self.serial, {}).get("data"):
                if hvac_mode == HVACMode.OFF:
                    dev_data["power"] = 1
                    dev_data["status"] = "off"
                    dev_data["mode"] = 0
                elif hvac_mode == HVACMode.AUTO:
                    dev_data["power"] = 2
                    dev_data["status"] = "none"
                    dev_data["mode"] = 1
                elif hvac_mode == HVACMode.HEAT:
                    dev_data["power"] = 2
                    dev_data["status"] = "none"
                    dev_data["mode"] = 0
            self.async_write_ha_state()
            await asyncio.sleep(0.5)
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set HVAC mode for %s: %s", self.name, resp.error_message)

    async def async_set_preset_mode(self, preset_mode: str) -> None:
        """Set new preset mode."""
        target_preset = "ice" if preset_mode == PRESET_AWAY else preset_mode
        resp = await self.hass.async_add_executor_job(
            self.coordinator.api.set_preset_mode,
            self.serial,
            target_preset,
            self.device_state,
        )
        if resp.success:
            if dev_data := self.coordinator.data.get(self.serial, {}).get("data"):
                dev_data["power"] = 2
                dev_data["mode"] = 0
                dev_data["status"] = target_preset
            self.async_write_ha_state()
            await asyncio.sleep(0.5)
            await self.coordinator.async_request_refresh()
        else:
            _LOGGER.error("Failed to set preset mode for %s: %s", self.name, resp.error_message)


    async def async_turn_on(self) -> None:
        """Turn the entity on."""
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self) -> None:
        """Turn the entity off."""
        await self.async_set_hvac_mode(HVACMode.OFF)
