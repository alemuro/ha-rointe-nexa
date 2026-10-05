"""DataUpdateCoordinator for Rointe Nexa."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .rointe_nexa import NexaAPI, NexaDevice

_LOGGER = logging.getLogger(__name__)


class RointeDataUpdateCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Class to manage fetching Rointe Nexa device data with real-time push."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, api: NexaAPI, entry: ConfigEntry) -> None:
        """Initialize coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.api = api
        self.config_entry = entry
        self.devices: list[NexaDevice] = []

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch data from Rointe API and Firebase RTDB."""
        try:
            # Discover devices if not already discovered
            if not self.devices:
                dev_resp = await self.hass.async_add_executor_job(self.api.get_devices)
                if not dev_resp.success:
                    raise UpdateFailed(f"Error discovering devices: {dev_resp.error_message}")
                self.devices = dev_resp.data

            # Fetch telemetry for all devices
            data_resp = await self.hass.async_add_executor_job(
                self.api.get_all_devices_data, self.devices
            )
            if not data_resp.success:
                raise UpdateFailed(f"Error fetching device states: {data_resp.error_message}")

            # Start real-time stream if not running yet
            if not self.api._stream_running:
                self.api._stream_cache = dict(data_resp.data)
                self.api.start_stream(self.devices, self._handle_stream_update)

            return data_resp.data

        except Exception as err:
            raise UpdateFailed(f"Communication error with Rointe Nexa: {err}") from err

    def _handle_stream_update(self, new_cache: dict[str, dict[str, Any]]) -> None:
        """Handle real-time update push from Firebase WebSocket."""
        self.hass.loop.call_soon_threadsafe(self.async_set_updated_data, new_cache)
