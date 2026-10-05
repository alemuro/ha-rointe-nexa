"""Rointe Nexa API client."""
from __future__ import annotations

import copy
import json
import logging
import ssl
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import requests
import websocket

try:
    from .const import (
        FIREBASE_API_KEY,
        FIREBASE_AUTH_URL,
        FIREBASE_DB_URL,
        NEXA_INSTALLATIONS_URL,
        NEXA_LOGIN_URL,
        PRESET_COMFORT,
        PRESET_ECO,
        PRESET_ICE,
    )
except (ImportError, ValueError):
    from const import (
        FIREBASE_API_KEY,
        FIREBASE_AUTH_URL,
        FIREBASE_DB_URL,
        NEXA_INSTALLATIONS_URL,
        NEXA_LOGIN_URL,
        PRESET_COMFORT,
        PRESET_ECO,
        PRESET_ICE,
    )

_LOGGER = logging.getLogger(__name__)


@dataclass
class ApiResponse:
    """API response wrapper."""
    success: bool
    data: Any = None
    error_message: str | None = None


@dataclass
class NexaDevice:
    """Representation of a Rointe Nexa device."""
    id: str
    name: str
    serial_number: str
    mac: str
    zone_id: str | None = None
    zone_name: str | None = None
    installation_id: str | None = None
    installation_name: str | None = None


class NexaAPI:
    """Rointe Nexa API client."""

    def __init__(self, username: str, password: str) -> None:
        """Initialize the API client."""
        self.username = username
        self.password = password
        self._nexa_token: str | None = None
        self._user_id: str | None = None
        self._firebase_token: str | None = None
        self._token_expiry: datetime | None = None
        self._devices: list[NexaDevice] = []

        # Real-time WebSocket stream management
        self._stream_ws: websocket.WebSocketApp | None = None
        self._stream_thread: threading.Thread | None = None
        self._stream_running: bool = False
        self._stream_cache: dict[str, dict[str, Any]] = {}
        self._stream_callback: Callable[[dict[str, dict[str, Any]]], None] | None = None
        self._req_counter: int = 10

    def initialize_authentication(self) -> ApiResponse:
        """Authenticate with Nexa API and Firebase."""
        try:
            # Step 1: Login to Nexa API
            login_response = requests.post(
                NEXA_LOGIN_URL,
                json={
                    "email": self.username,
                    "password": self.password,
                    "push": "",
                    "migrate": False,
                },
                timeout=30,
            )

            if login_response.status_code != 200:
                _LOGGER.error("Nexa login failed: %s", login_response.text)
                return ApiResponse(
                    success=False,
                    error_message=f"Nexa login failed: {login_response.text}",
                )

            login_data = login_response.json()
            self._nexa_token = login_data["data"]["token"]
            self._user_id = login_data["data"]["user"]["id"]

            # Step 2: Authenticate with Firebase using user_id credentials
            firebase_response = requests.post(
                f"{FIREBASE_AUTH_URL}?key={FIREBASE_API_KEY}",
                json={
                    "returnSecureToken": True,
                    "email": f"{self._user_id}@rointe.com",
                    "password": self._user_id,
                    "clientType": "CLIENT_TYPE_WEB",
                },
                timeout=30,
            )

            if firebase_response.status_code != 200:
                _LOGGER.error("Firebase auth failed: %s", firebase_response.text)
                return ApiResponse(
                    success=False,
                    error_message=f"Firebase auth failed: {firebase_response.text}",
                )

            fb_data = firebase_response.json()
            self._firebase_token = fb_data["idToken"]
            self._token_expiry = datetime.now() + timedelta(minutes=50)

            return ApiResponse(success=True, data={"user_id": self._user_id})

        except Exception as e:
            _LOGGER.exception("Unexpected error during authentication: %s", e)
            return ApiResponse(success=False, error_message=str(e))

    def _ensure_authenticated(self, force: bool = False) -> bool:
        """Ensure we have valid tokens."""
        if (
            force
            or self._nexa_token is None
            or self._firebase_token is None
            or self._token_expiry is None
            or datetime.now() >= self._token_expiry
        ):
            return self.initialize_authentication().success
        return True

    def get_installations(self) -> ApiResponse:
        """Fetch installations from Nexa API."""
        if not self._ensure_authenticated():
            return ApiResponse(success=False, error_message="Authentication failed")

        try:
            resp = requests.get(
                NEXA_INSTALLATIONS_URL,
                headers={"token": self._nexa_token},
                timeout=30,
            )
            if resp.status_code == 401:
                if self.initialize_authentication().success:
                    resp = requests.get(
                        NEXA_INSTALLATIONS_URL,
                        headers={"token": self._nexa_token},
                        timeout=30,
                    )

            if resp.status_code != 200:
                return ApiResponse(
                    success=False,
                    error_message=f"Failed to fetch installations: {resp.status_code} {resp.text}",
                )

            return ApiResponse(success=True, data=resp.json().get("data", []))
        except Exception as e:
            return ApiResponse(success=False, error_message=str(e))

    def get_devices(self) -> ApiResponse:
        """Discover and return all devices across installations and zones."""
        inst_resp = self.get_installations()
        if not inst_resp.success:
            return inst_resp

        devices: list[NexaDevice] = []

        def extract_devices_from_zones(
            zones: list[dict],
            inst_id: str,
            inst_name: str,
        ) -> None:
            for zone in zones:
                zone_id = zone.get("id")
                zone_name = zone.get("name")

                for dev in zone.get("devices", []):
                    serial = dev.get("serialNumber") or dev.get("mac")
                    if serial:
                        devices.append(
                            NexaDevice(
                                id=dev.get("id", serial),
                                name=dev.get("name", f"Radiator {serial[-6:]}"),
                                serial_number=serial,
                                mac=dev.get("mac", serial),
                                zone_id=zone_id,
                                zone_name=zone_name,
                                installation_id=inst_id,
                                installation_name=inst_name,
                            )
                        )

                if sub_zones := zone.get("zones"):
                    extract_devices_from_zones(sub_zones, inst_id, inst_name)

        for inst in inst_resp.data:
            inst_id = inst.get("id")
            inst_name = inst.get("name")
            if zones := inst.get("zones"):
                extract_devices_from_zones(zones, inst_id, inst_name)

        self._devices = devices
        return ApiResponse(success=True, data=devices)

    def get_device_data(self, serial_number: str) -> ApiResponse:
        """Fetch device real-time state from Firebase RTDB REST API."""
        if not self._ensure_authenticated():
            return ApiResponse(success=False, error_message="Authentication failed")

        url = f"{FIREBASE_DB_URL}/devices/{serial_number}.json?auth={self._firebase_token}"
        try:
            resp = requests.get(url, timeout=15)
            if resp.status_code == 401:
                if self.initialize_authentication().success:
                    url = f"{FIREBASE_DB_URL}/devices/{serial_number}.json?auth={self._firebase_token}"
                    resp = requests.get(url, timeout=15)

            if resp.status_code != 200:
                return ApiResponse(
                    success=False,
                    error_message=f"Failed to fetch device data: {resp.status_code} {resp.text}",
                )

            data = resp.json()
            if data is None:
                return ApiResponse(success=False, error_message="Device not found in database")

            return ApiResponse(success=True, data=data)
        except Exception as e:
            return ApiResponse(success=False, error_message=str(e))

    def get_all_devices_data(self, devices: list[NexaDevice] | None = None) -> ApiResponse:
        """Fetch real-time state for all devices."""
        dev_list = devices if devices is not None else self._devices
        all_data: dict[str, dict[str, Any]] = {}

        for dev in dev_list:
            resp = self.get_device_data(dev.serial_number)
            if resp.success and resp.data:
                all_data[dev.serial_number] = resp.data
            else:
                _LOGGER.warning(
                    "Could not fetch data for device %s (%s): %s",
                    dev.name,
                    dev.serial_number,
                    resp.error_message,
                )

        return ApiResponse(success=True, data=all_data)

    # Real-Time WebSocket Streaming & Command Delivery

    def start_stream(
        self,
        devices: list[NexaDevice],
        on_update_callback: Callable[[dict[str, dict[str, Any]]], None],
    ) -> None:
        """Start the persistent Firebase WebSocket stream for instant updates."""
        self._devices = devices
        self._stream_callback = on_update_callback
        if self._stream_running:
            return

        self._stream_running = True
        self._stream_thread = threading.Thread(
            target=self._stream_loop,
            daemon=True,
            name="RointeNexaStream",
        )
        self._stream_thread.start()
        _LOGGER.info("Started real-time WebSocket push stream for Rointe Nexa")

    def stop_stream(self) -> None:
        """Stop the persistent stream."""
        self._stream_running = False
        if self._stream_ws:
            try:
                self._stream_ws.close()
            except Exception:
                pass
        self._stream_ws = None
        _LOGGER.info("Stopped real-time WebSocket push stream for Rointe Nexa")

    def _handle_stream_message(self, message: str) -> None:
        """Parse incoming Firebase WebSocket event and update cache."""
        try:
            msg = json.loads(message)
            if msg.get("t") == "d" and "d" in msg:
                d = msg["d"]
                if "b" in d and "p" in d["b"]:
                    path = d["b"]["p"]
                    data = d["b"].get("d")
                    if path and data is not None:
                        self._apply_delta_to_cache(path, data)
        except Exception as e:
            _LOGGER.debug("Error parsing stream message: %s", e)

    def _apply_delta_to_cache(self, path: str, data: Any) -> None:
        """Apply received delta to the live memory cache and notify coordinator."""
        parts = path.strip("/").split("/")
        if len(parts) >= 2 and parts[0] == "devices":
            serial = parts[1]
            if len(parts) == 2 and isinstance(data, dict):
                # Full device object: devices/{serial}
                self._stream_cache[serial] = data
            elif len(parts) == 3 and parts[2] == "data" and isinstance(data, dict):
                # Merge dict: devices/{serial}/data
                self._stream_cache.setdefault(serial, {}).setdefault("data", {}).update(data)
            elif len(parts) == 4 and parts[2] == "data":
                # Specific property: devices/{serial}/data/{field}
                field = parts[3]
                self._stream_cache.setdefault(serial, {}).setdefault("data", {})[field] = data

            if self._stream_callback:
                self._stream_callback(copy.deepcopy(self._stream_cache))

    def _stream_loop(self) -> None:
        """Loop keeping the WebSocket connection alive with auto-reconnect."""
        while self._stream_running:
            try:
                if not self._ensure_authenticated():
                    time.sleep(5)
                    continue

                ws_url = f"{FIREBASE_DB_URL.replace('https://', 'wss://')}/.ws?v=5&ns=rointe-v3-prod-default-rtdb"

                def on_open(ws):
                    try:
                        # 1. Authenticate
                        ws.send(json.dumps({
                            "t": "d",
                            "d": {"r": 1, "a": "auth", "b": {"cred": self._firebase_token}},
                        }))
                        time.sleep(0.2)
                        # 2. Subscribe to each device
                        for idx, dev in enumerate(self._devices, start=2):
                            ws.send(json.dumps({
                                "t": "d",
                                "d": {"r": idx, "a": "q", "b": {"p": f"/devices/{dev.serial_number}", "h": ""}},
                            }))
                            time.sleep(0.05)
                    except Exception as e:
                        _LOGGER.debug("Error during stream on_open: %s", e)

                def on_message(ws, msg):
                    self._handle_stream_message(msg)

                def on_error(ws, error):
                    _LOGGER.debug("Firebase stream error: %s", error)

                def on_close(ws, close_status, close_msg):
                    _LOGGER.debug("Firebase stream closed: %s %s", close_status, close_msg)

                self._stream_ws = websocket.WebSocketApp(
                    ws_url,
                    on_open=on_open,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close,
                )

                self._stream_ws.run_forever(
                    sslopt={"cert_reqs": ssl.CERT_NONE},
                    ping_interval=20,
                    ping_timeout=10,
                )

            except Exception as e:
                _LOGGER.debug("Firebase stream loop exception: %s", e)

            if self._stream_running:
                time.sleep(3)

    def send_command(self, serial_number: str, fields: list[tuple[str, Any]]) -> ApiResponse:
        """Send command over the active stream WebSocket, or fallback to temporary connection."""
        ws = self._stream_ws
        if ws and hasattr(ws, "sock") and ws.sock and ws.sock.connected:
            try:
                for field, value in fields:
                    self._req_counter += 1
                    ws.send(json.dumps({
                        "t": "d",
                        "d": {
                            "r": self._req_counter,
                            "a": "p",
                            "b": {"p": f"/devices/{serial_number}/data/{field}", "d": value},
                        },
                    }))
                    time.sleep(0.08)
                return ApiResponse(success=True)
            except Exception as e:
                _LOGGER.warning("Failed to send over live stream socket, falling back: %s", e)

        # Fallback to one-shot websocket
        return self._write_via_websocket(serial_number, fields)

    def _write_via_websocket(self, serial_number: str, fields: list[tuple[str, Any]]) -> ApiResponse:
        """Write fields to Firebase RTDB in sequential order via a one-shot WebSocket."""
        if not self._ensure_authenticated():
            return ApiResponse(success=False, error_message="Authentication failed")

        ws_done = threading.Event()
        ws_connected = threading.Event()
        errors: list[str] = []
        closing = [False]

        def on_message(ws, message):
            try:
                msg = json.loads(message)
                if msg.get("t") == "d" and "d" in msg:
                    d = msg["d"]
                    if d.get("r") == len(fields) + 1:
                        ws_done.set()
            except Exception:
                pass

        def on_error(ws, error):
            if not closing[0] and error:
                err_str = str(error)
                if "NoneType" not in err_str:
                    errors.append(err_str)
                    ws_done.set()

        def on_close(ws, code, msg):
            ws_done.set()

        def on_open(ws):
            ws_connected.set()
            try:
                ws.send(json.dumps({
                    "t": "d",
                    "d": {"r": 1, "a": "auth", "b": {"cred": self._firebase_token}},
                }))
                time.sleep(0.2)

                for idx, (field, value) in enumerate(fields, start=2):
                    ws.send(json.dumps({
                        "t": "d",
                        "d": {
                            "r": idx,
                            "a": "p",
                            "b": {"p": f"/devices/{serial_number}/data/{field}", "d": value},
                        },
                    }))
                    time.sleep(0.08)
            except Exception as e:
                errors.append(str(e))
                ws_done.set()

        def safe_close(ws):
            closing[0] = True
            try:
                if ws and hasattr(ws, "sock") and ws.sock:
                    ws.close()
            except Exception:
                pass

        ws_url = f"{FIREBASE_DB_URL.replace('https://', 'wss://')}/.ws?v=5&ns=rointe-v3-prod-default-rtdb"
        ws = websocket.WebSocketApp(
            ws_url,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )

        ws_thread = threading.Thread(
            target=lambda: ws.run_forever(sslopt={"cert_reqs": ssl.CERT_NONE}),
            daemon=True,
        )
        ws_thread.start()

        if not ws_connected.wait(timeout=5):
            safe_close(ws)
            return ApiResponse(success=False, error_message="WebSocket connection timeout")

        ws_done.wait(timeout=4)
        safe_close(ws)
        ws_thread.join(timeout=1)

        if errors:
            return ApiResponse(success=False, error_message="; ".join(errors))

        return ApiResponse(success=True)

    # High-level control methods

    def set_temperature(self, serial_number: str, target_temp: float) -> ApiResponse:
        """Set device target temperature (switches to manual mode, heating power)."""
        return self.send_command(
            serial_number,
            [
                ("mode", 0),
                ("power", 2),
                ("status", "none"),
                ("temp", float(target_temp)),
            ],
        )

    def set_hvac_mode(self, serial_number: str, mode: str) -> ApiResponse:
        """Set device HVAC mode ('off', 'heat', or 'auto')."""
        mode_lower = mode.lower()
        if mode_lower == "off":
            return self.send_command(
                serial_number,
                [
                    ("mode", 0),
                    ("power", 1),
                    ("status", "off"),
                ],
            )
        elif mode_lower == "heat":
            return self.send_command(
                serial_number,
                [
                    ("mode", 0),
                    ("power", 2),
                    ("status", "none"),
                ],
            )
        elif mode_lower == "auto":
            return self.send_command(
                serial_number,
                [
                    ("mode", 1),
                    ("power", 2),
                    ("status", "none"),
                ],
            )
        return ApiResponse(success=False, error_message=f"Unknown HVAC mode: {mode}")

    def set_preset_mode(
        self,
        serial_number: str,
        preset: str,
        current_data: dict[str, Any] | None = None,
    ) -> ApiResponse:
        """Set preset mode ('comfort', 'eco', 'ice'/'away', or 'none')."""
        preset_lower = preset.lower()
        data = current_data.get("data", {}) if current_data else {}

        if preset_lower == PRESET_COMFORT:
            comfort_temp = float(data.get("comfort", 21.5))
            return self.send_command(
                serial_number,
                [
                    ("mode", 0),
                    ("power", 2),
                    ("status", "comfort"),
                    ("temp", comfort_temp),
                ],
            )
        elif preset_lower == PRESET_ECO:
            eco_temp = float(data.get("eco", 18.5))
            return self.send_command(
                serial_number,
                [
                    ("mode", 0),
                    ("power", 2),
                    ("status", "eco"),
                    ("temp", eco_temp),
                ],
            )
        elif preset_lower in (PRESET_ICE, "away"):
            ice_temp = float(data.get("ice", 7.0))
            return self.send_command(
                serial_number,
                [
                    ("mode", 0),
                    ("power", 2),
                    ("status", "ice"),
                    ("temp", ice_temp),
                ],
            )
        elif preset_lower in ("none", "manual"):
            return self.send_command(
                serial_number,
                [
                    ("mode", 0),
                    ("power", 2),
                    ("status", "none"),
                ],
            )

        return ApiResponse(success=False, error_message=f"Unknown preset mode: {preset}")

    def set_preset_temperature(
        self,
        serial_number: str,
        preset_type: str,
        temperature: float,
    ) -> ApiResponse:
        """Set temperature for a preset type ('comfort', 'eco', or 'ice')."""
        preset_lower = preset_type.lower()
        if preset_lower in (PRESET_COMFORT, PRESET_ECO, PRESET_ICE):
            return self.send_command(
                serial_number,
                [(preset_lower, float(temperature))],
            )
        return ApiResponse(success=False, error_message=f"Unknown preset type: {preset_type}")

    def set_keypad_lock(self, serial_number: str, locked: bool) -> ApiResponse:
        """Lock or unlock the physical keypad on the radiator."""
        return self.send_command(serial_number, [("block_local", bool(locked))])

    def set_open_window_detection(self, serial_number: str, enabled: bool) -> ApiResponse:
        """Enable or disable open window detection."""
        return self.send_command(serial_number, [("windows_open_mode", bool(enabled))])