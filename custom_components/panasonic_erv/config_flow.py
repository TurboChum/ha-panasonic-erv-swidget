"""Config flow for Panasonic ERV integration."""

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .api import PanasonicERVApi, PanasonicERVApiError
from .const import (
    CONF_BOOST_RECOVERY,
    CONF_CFM_ALERT_DURATION,
    CONF_CFM_ALERT_THRESHOLD,
    CONF_DEVICE_NAME,
    CONF_DEVICE_URL,
    CONF_FW_VERSION,
    CONF_MAC,
    CONF_MODEL_NAME,
    CONF_POLL_INTERVAL,
    CONF_RETRY_COUNT,
    CONF_VERIFY_DELAY,
    DEFAULT_BOOST_RECOVERY,
    DEFAULT_CFM_ALERT_DURATION,
    DEFAULT_CFM_ALERT_THRESHOLD,
    DEFAULT_NAME,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_RETRY_COUNT,
    DEFAULT_VERIFY_DELAY,
    DOMAIN,
)


class PanasonicERVConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a Panasonic ERV config flow."""

    VERSION = 1

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            session = aiohttp_client.async_get_clientsession(self.hass)
            api = PanasonicERVApi(session, user_input[CONF_DEVICE_URL])
            try:
                summary = await api.async_get_summary()
            except PanasonicERVApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                mac = summary.get("mac", "")
                if mac:
                    await self.async_set_unique_id(mac)
                    self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title=user_input[CONF_DEVICE_NAME],
                    data={
                        CONF_DEVICE_NAME: user_input[CONF_DEVICE_NAME],
                        CONF_DEVICE_URL: user_input[CONF_DEVICE_URL],
                        CONF_MAC: mac,
                        CONF_MODEL_NAME: summary.get("host", {}).get("type", "ERV"),
                        CONF_FW_VERSION: summary.get("version", ""),
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_DEVICE_NAME, default=DEFAULT_NAME): str,
                    vol.Required(CONF_DEVICE_URL): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return PanasonicERVOptionsFlow(config_entry)


class PanasonicERVOptionsFlow(config_entries.OptionsFlow):
    """Handle Panasonic ERV options."""

    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options = self.config_entry.options
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_POLL_INTERVAL,
                        default=options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL),
                    ): vol.All(int, vol.Range(min=10, max=3600)),
                    vol.Required(
                        CONF_RETRY_COUNT,
                        default=options.get(CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT),
                    ): vol.All(int, vol.Range(min=1, max=10)),
                    vol.Required(
                        CONF_VERIFY_DELAY,
                        default=options.get(CONF_VERIFY_DELAY, DEFAULT_VERIFY_DELAY),
                    ): vol.All(int, vol.Range(min=1, max=30)),
                    vol.Required(
                        CONF_BOOST_RECOVERY,
                        default=options.get(CONF_BOOST_RECOVERY, DEFAULT_BOOST_RECOVERY),
                    ): bool,
                    vol.Required(
                        CONF_CFM_ALERT_THRESHOLD,
                        default=options.get(CONF_CFM_ALERT_THRESHOLD, DEFAULT_CFM_ALERT_THRESHOLD),
                    ): vol.All(int, vol.Range(min=5, max=30)),
                    vol.Required(
                        CONF_CFM_ALERT_DURATION,
                        default=options.get(CONF_CFM_ALERT_DURATION, DEFAULT_CFM_ALERT_DURATION),
                    ): vol.All(int, vol.Range(min=30, max=300)),
                }
            ),
        )
