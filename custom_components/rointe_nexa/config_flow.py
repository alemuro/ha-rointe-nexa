"""Config flow for Rointe Nexa integration."""
from __future__ import annotations

import logging
from typing import Any

import requests
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_PASSWORD, CONF_USERNAME, DOMAIN
from .rointe_nexa import NexaAPI

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str,
    }
)


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Rointe Nexa."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                api = NexaAPI(user_input[CONF_USERNAME], user_input[CONF_PASSWORD])
                resp = await self.hass.async_add_executor_job(
                    api.initialize_authentication
                )

                if not resp.success:
                    if "401" in str(resp.error_message) or "login failed" in str(resp.error_message).lower():
                        errors["base"] = "invalid_auth"
                    else:
                        errors["base"] = "cannot_connect"
                else:
                    user_id = (
                        resp.data.get("user_id")
                        if resp.data
                        else user_input[CONF_USERNAME]
                    )

                    await self.async_set_unique_id(user_id)
                    self._abort_if_unique_id_configured()

                    return self.async_create_entry(
                        title=user_input[CONF_USERNAME], data=user_input
                    )

            except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected exception in config flow")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )
