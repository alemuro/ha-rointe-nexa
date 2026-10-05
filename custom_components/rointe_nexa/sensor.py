"""Sensors for Rointe Nexa."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS_MILLIWATT,
    EntityCategory,
    UnitOfPower,
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
                RointeCurrentPowerSensor(coordinator, device),
                RointeNominalPowerSensor(coordinator, device),
                RointeEffectivePowerSensor(coordinator, device),
                RointeWifiSignalSensor(coordinator, device),
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


class RointeCurrentPowerSensor(RointeEntity, SensorEntity):
    """Sensor for current instant power consumption."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_translation_key = "power"

    def __init__(self, coordinator: RointeDataUpdateCoordinator, device) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, device, "current_power")
        self._attr_name = "Power"

    @property
    def native_value(self) -> float | None:
        """Return current power (nominal effective power when heating, 0 when idle/off)."""
        power_state = self.device_data.get("power")
        warming = self.device_data.get("status_warming")
        status = self.device_data.get("status")

        if power_state == 1 or status == "off":
            return 0.0

        if warming == 2:
            eff_power = self.device_data.get("nominal_effective_power") or self.device_data.get("nominal_power")
            try:
                return float(eff_power) if eff_power is not None else None
            except (ValueError, TypeError):
                return None

        return 0.0


class RointeNominalPowerSensor(RointeEntity, SensorEntity):
    """Sensor for radiator nominal power."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_translation_key = "nominal_power"

    def __init__(self, coordinator: RointeDataUpdateCoordinator, device) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, device, "nominal_power")
        self._attr_name = "Nominal Power"

    @property
    def native_value(self) -> float | None:
        """Return nominal power."""
        power = self.device_data.get("nominal_power")
        try:
            return float(power) if power is not None else None
        except (ValueError, TypeError):
            return None


class RointeEffectivePowerSensor(RointeEntity, SensorEntity):
    """Sensor for radiator nominal effective power."""

    _attr_device_class = SensorDeviceClass.POWER
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_translation_key = "effective_power"

    def __init__(self, coordinator: RointeDataUpdateCoordinator, device) -> None:
        """Initialize sensor."""
        super().__init__(coordinator, device, "effective_power")
        self._attr_name = "Effective Power"

    @property
    def native_value(self) -> float | None:
        """Return nominal effective power."""
        power = self.device_data.get("nominal_effective_power")
        try:
            return float(power) if power is not None else None
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
