"""Config flow for Panasonic ERV integration."""

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_URL
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_DEVICE_NAME, CONF_DEVICE_URL, DOMAIN

class PanasonicERVConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Panasonic ERV config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        if user_input is not None:
            return self.async_create_entry(
                title=user_input[CONF_DEVICE_NAME],
                data={
                    CONF_DEVICE_NAME: user_input[CONF_DEVICE_NAME],
                    CONF_DEVICE_URL: user_input[CONF_DEVICE_URL],
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=self._get_data_schema(),
        )

    @staticmethod
    @callback
    def _get_data_schema():
        from voluptuous import Required, Schema

        return Schema(
            {
                Required(CONF_DEVICE_NAME, default="Panasonic ERV"): str,
                Required(CONF_DEVICE_URL): str,
            }
        )
