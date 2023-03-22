from typing import Any, Dict, Optional

import logging
import voluptuous as vol

from homeassistant import config_entries, exceptions
from homeassistant.const import CONF_PASSWORD, CONF_URL, CONF_USERNAME
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import AbortFlow, FlowResult

from ihcsdk.ihccontroller import IHCController

from .const import CONF_AUTOSETUP, DOMAIN
from .util import get_controller_serial

_LOGGER = logging.getLogger(__name__)

CONFIG_FLOW_VERSION = 1

DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_URL, default="http://192.168.1.3"): str,
        vol.Required(CONF_USERNAME, default=""): str,
        vol.Required(CONF_PASSWORD, default=""): str,
        vol.Optional(CONF_AUTOSETUP, default=True): bool,
    }
)


def do_validate(hass: HomeAssistant, user_input: Dict[str, Any]) -> str:
    url = user_input[CONF_URL]
    username = user_input[CONF_USERNAME]
    password = user_input[CONF_PASSWORD]

    if not IHCController.is_ihc_controller(url):
        raise CannotConnect()

    ihc_controller = IHCController(url, username, password)
    try:
        if not ihc_controller.authenticate():
            raise InvalidAuth()
        serial = get_controller_serial(ihc_controller)
    finally:
        ihc_controller.disconnect()

    return serial


class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1
    CONNECTION_CLASS = config_entries.CONN_CLASS_LOCAL_PUSH

    async def async_step_user(self, user_input: Optional[Dict[str, Any]] = None) -> FlowResult:
        errors = {}

        if user_input is not None:
            try:
                serialnumber = await self.hass.async_add_executor_job(
                    do_validate, self.hass, user_input
                )
                await self.async_set_unique_id(serialnumber)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title="IHC Controller", data=user_input)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            except InvalidAuth:
                errors["base"] = "invalid_auth"
            except AbortFlow:
                errors["base"] = "already_setup"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )


class CannotConnect(exceptions.HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(exceptions.HomeAssistantError):
    """Error to indicate we cannot authenticate."""
