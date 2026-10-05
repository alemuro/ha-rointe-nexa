import os
import sys
import json
import logging
from pprint import pprint

# Automatically load .env if present and environment variables not set
env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k, v.strip("\"'"))

# Add custom_components/rointe_nexa to path
sys.path.append(os.path.join(os.path.dirname(__file__), "custom_components", "rointe_nexa"))

try:
    import rointe_nexa
    NexaAPI = rointe_nexa.NexaAPI
except ImportError as e:
    print(f"Error: Could not import NexaAPI: {e}")
    sys.exit(1)

logging.basicConfig(level=logging.INFO)

def main():
    username = os.environ.get("ROINTE_USERNAME")
    password = os.environ.get("ROINTE_PASSWORD")

    if not username or not password:
        print("Please set ROINTE_USERNAME and ROINTE_PASSWORD in .env or environment variables.")
        sys.exit(1)

    print(f"--- Attempting login for {username} ---")
    api = NexaAPI(username, password)

    auth_resp = api.initialize_authentication()
    if not auth_resp.success:
        print(f"Authentication failed: {auth_resp.error_message}")
        sys.exit(1)

    print("Authentication successful!")
    print(f"User ID: {auth_resp.data.get('user_id')}")
    print("-" * 50)

    print("--- Discovering Devices ---")
    devices_resp = api.get_devices()
    if not devices_resp.success:
        print(f"Discovery failed: {devices_resp.error_message}")
        sys.exit(1)

    devices = devices_resp.data
    print(f"Discovered {len(devices)} device(s):")
    for d in devices:
        print(f"  • Name: {d.name}")
        print(f"    Serial: {d.serial_number}")
        print(f"    MAC: {d.mac}")
        print(f"    Zone: {d.zone_name}")
        print(f"    Installation: {d.installation_name}")

    print("-" * 50)
    print("--- Fetching Real-Time State for All Devices ---")
    all_data_resp = api.get_all_devices_data(devices)
    if not all_data_resp.success:
        print(f"Failed to fetch data: {all_data_resp.error_message}")
        sys.exit(1)

    for serial, state in all_data_resp.data.items():
        data = state.get("data", {})
        firmware = state.get("firmware", {})
        print(f"\n[Device {serial}]")
        print(f"  Firmware Version: {firmware.get('firmware_version')}")
        print(f"  Hardware Version: {firmware.get('hardware_version')}")
        print(f"  Ambient Temp: {data.get('temp_probe')} °C")
        print(f"  Target Temp:  {data.get('temp')} °C")
        print(f"  Surface Temp: {data.get('temp_surface')} °C")
        print(f"  Power State:  {data.get('power')} (1=Off/Standby, 2=On)")
        print(f"  Mode:         {data.get('mode')} (0=Manual, 1=Auto/Schedule)")
        print(f"  Status:       {data.get('status')} (Preset: eco/comfort/ice/none)")
        print(f"  Warming:      {data.get('status_warming')} (2=Heating, 0/1=Idle)")
        print(f"  Comfort Temp: {data.get('comfort')} °C")
        print(f"  Eco Temp:     {data.get('eco')} °C")
        print(f"  Ice Temp:     {data.get('ice')} °C")
        print(f"  Keypad Lock:  {data.get('block_local')}")
        print(f"  Window Mode:  {data.get('windows_open_mode')}")
        print(f"  Window Open:  {data.get('windows_open_status')}")
        print(f"  Nominal Power:{data.get('nominal_power')} W")
        print(f"  WiFi Signal:  {data.get('wifisignal')} dBm ({data.get('wifissid')})")

    print("\nTest completed successfully!")

if __name__ == "__main__":
    main()
