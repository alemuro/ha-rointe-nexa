"""Constants for the Rointe Nexa integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "rointe_nexa"

CONF_USERNAME = "username"
CONF_PASSWORD = "password"

DEFAULT_SCAN_INTERVAL = timedelta(seconds=30)

# Preset modes
PRESET_ECO = "eco"
PRESET_COMFORT = "comfort"
PRESET_ICE = "ice"

# Firebase constants
FIREBASE_AUTH_URL = "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
FIREBASE_API_KEY = "AIzaSyC0aaLXKB8Vatf2xSn1QaFH1kw7rADZlrY"
FIREBASE_DB_URL = "https://rointe-v3-prod-default-rtdb.europe-west1.firebasedatabase.app"

# Nexa API endpoints
NEXA_API_URL = "https://rointenexa.com/api"
NEXA_LOGIN_URL = f"{NEXA_API_URL}/user/login"
NEXA_INSTALLATIONS_URL = f"{NEXA_API_URL}/installations"
