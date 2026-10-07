"""Sensors for Rointe Nexa."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfTemperature,
)
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
    """Set up Rointe Nexa sensors."""
    coordinator: RointeDataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = []
    for device in coordinator.devices:
        entities.extend(
            [
                RointeSurfaceTempSensor(coordinator, device),
                RointeWifiSignalSensor(coordinator, device),
                RointeScheduleSensor(coordinator, device),
            ]
        )

    async_add_entities(entities)


class RointeSurfaceTempSensor(RointeEntity, SensorEntity):
    """Sensor for radiator surface temperature."""

    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_translation_key = "surface_temperature"

    def __init__(self, coordinator: RointeDataUpdateCoordinator, device) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, device, "surface_temp")
        self._attr_name = "Surface Temperature"

    @property
    def native_value(self) -> float | None:
        """Return the surface temperature."""
        temp = self.device_data.get("temp_surface")
        try:
            return float(temp) if temp is not None else None
        except (ValueError, TypeError):
            return None


class RointeWifiSignalSensor(RointeEntity, SensorEntity):
    """Sensor for WiFi signal strength."""

    _attr_device_class = SensorDeviceClass.SIGNAL_STRENGTH
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = SIGNAL_STRENGTH_DECIBELS_MILLIWATT
    _attr_translation_key = "wifi_signal"

    def __init__(self, coordinator: RointeDataUpdateCoordinator, device) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, device, "wifi_signal")
        self._attr_name = "WiFi Signal"

    @property
    def native_value(self) -> int | None:
        """Return WiFi signal in dBm."""
        signal = self.device_data.get("wifisignal")
        try:
            return int(signal) if signal is not None else None
        except (ValueError, TypeError):
            return None


class RointeScheduleSensor(RointeEntity, SensorEntity):
    """Sensor exposing radiator schedule and active programmed preset."""

    _attr_icon = "mdi:calendar-clock"
    _attr_translation_key = "schedule"

    _DAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]

    def __init__(self, coordinator: RointeDataUpdateCoordinator, device) -> None:
        """Initialize schedule sensor."""
        super().__init__(coordinator, device, "schedule")
        self._attr_name = "Schedule"

    def _parse_slot(self, code: str) -> str:
        """Map schedule character code to preset name."""
        char = code.upper()
        if char == "C":
            return "Comfort"
        if char == "E":
            return "Eco"
        if char in ("I", "A", "O", "0"):
            return "Ice"
        return "Unknown"

    def _get_raw_schedule(self) -> list[str] | None:
        """Return raw schedule list from device data."""
        sched = self.device_data.get("schedule")
        if isinstance(sched, list):
            return sched
        if isinstance(sched, dict):
            return [sched.get(str(i), "") for i in range(7)]
        return None

    @property
    def native_value(self) -> str | None:
        """Return current programmed preset name."""
        sched = self._get_raw_schedule()
        if not sched:
            return None

        now = datetime.now()
        weekday = now.weekday()
        hour = now.hour

        if len(sched) > weekday and len(sched[weekday]) > hour:
            return self._parse_slot(sched[weekday][hour])
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return schedule details and upcoming changes."""
        sched = self._get_raw_schedule()
        if not sched:
            return {}

        now = datetime.now()
        weekday = now.weekday()
        hour = now.hour

        schedule_by_day = {
            day_name: sched[idx] if len(sched) > idx else ""
            for idx, day_name in enumerate(self._DAYS)
        }

        today_str = sched[weekday] if len(sched) > weekday else ""
        today_hourly = {
            f"{h:02d}:00": self._parse_slot(today_str[h]) if len(today_str) > h else "Unknown"
            for h in range(24)
        }

        current_preset = self.native_value

        # Calculate next scheduled change within the next 7 days (168 hours)
        next_change = None
        for offset in range(1, 168):
            target_hour = (hour + offset) % 24
            target_day_idx = (weekday + (hour + offset) // 24) % 7
            day_str = sched[target_day_idx] if len(sched) > target_day_idx else ""
            if len(day_str) > target_hour:
                target_slot = self._parse_slot(day_str[target_hour])
                if target_slot != current_preset:
                    next_change = {
                        "day": self._DAYS[target_day_idx],
                        "time": f"{target_hour:02d}:00",
                        "preset": target_slot,
                        "in_hours": offset,
                    }
                    break

        attrs: dict[str, Any] = {
            "current_day": self._DAYS[weekday],
            "current_hour": hour,
            "current_preset": current_preset,
            "schedule": schedule_by_day,
            "today_schedule": today_str,
            "today_hourly": today_hourly,
        }

        if next_change:
            attrs["next_change"] = f"{next_change['time']} ({next_change['preset']})"
            attrs["next_change_detail"] = next_change

        return attrs

