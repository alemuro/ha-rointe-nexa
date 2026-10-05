# Rointe Nexa Custom Component for Home Assistant

Custom component for Home Assistant to integrate **Rointe Nexa** smart heating devices (radiators, towel rails, etc.).

## Features

### 🌡️ Climate (`climate`)
- **Modes**:
  - `Heat`: Manual setpoint heating mode.
  - `Auto`: Follows the internal Rointe schedule/programming.
  - `Off`: Standby mode.
- **Presets**:
  - `Comfort`: Switches to the configured Comfort temperature.
  - `Eco`: Switches to the configured Eco temperature.
  - `Away` (Anti-frost): Switches to the configured Ice / Anti-frost temperature (7 °C).
  - `None`: Manual temperature setpoint.
- **Action State**: Displays whether the radiator is actively heating (`heating`) or in standby/idle (`idle` / `off`).
- **Target Temperature**: Configurable between 7.0 °C and 30.0 °C in 0.5 °C steps.
- **Ambient Temperature**: Real-time room temperature from the radiator's built-in probe.

### ⚡ Sensors (`sensor`)
- **Power** (`W`): Estimated current power consumption (reports effective power when actively heating, 0 W when idle or off).
- **Nominal Power** (`W`): Rated radiator wattage (e.g. 1000 W).
- **Effective Power** (`W`): Effective power rating.
- **Surface Temperature** (`°C`): Radiator chassis/surface temperature.
- **WiFi Signal** (`dBm`): WiFi RSSI signal strength.

### 🔘 Binary Sensors (`binary_sensor`)
- **Heating**: Turns `on` whenever the radiator elements are actively heating.
- **Window Open**: Detects sudden temperature drops and reports if an open window is active.
- **Connectivity**: Online / connectivity status with the cloud backend.

### 🔒 Switches (`switch`)
- **Keypad Lock**: Locks or unlocks the physical buttons and touch screen on the radiator (child lock).
- **Open Window Detection**: Enables or disables the radiator's automatic open-window detection feature.

### 🎛️ Numbers (`number`)
- **Comfort Temperature**: Adjusts the default Comfort preset temperature setting.
- **Eco Temperature**: Adjusts the default Eco preset temperature setting.
- **Anti-frost Temperature**: Adjusts the default Ice / Anti-frost preset temperature setting.

---

## Installation

### Via HACS (Recommended)

1. Open **HACS** in your Home Assistant instance.
2. Click the three dots in the top right corner and select **Custom repositories**.
3. Enter the repository URL: `https://github.com/alemuro/ha-rointe-nexa`.
4. Select **Integration** as category and click **Add**.
5. Find **Rointe Nexa** in the integrations list and click **Download**.
6. Restart Home Assistant.

### Manual Installation

1. Copy the `custom_components/rointe_nexa` directory into your Home Assistant `<config>/custom_components/` folder.
2. Restart Home Assistant.

---

## Configuration

1. In Home Assistant, navigate to **Settings** -> **Devices & Services**.
2. Click **Add Integration** and search for **Rointe Nexa**.
3. Enter your Rointe Nexa account credentials (email and password).
4. Devices will be automatically discovered across all installations and zones.
