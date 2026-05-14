"""Config flow and options flow for the Panasonic ERV integration.

HA uses config flows to walk the user through setting up an integration via the
UI (Settings → Devices & Services → Add Integration).  This file defines two
flows:

  PanasonicERVConfigFlow  — the initial setup wizard (device name + URL).
  PanasonicERVOptionsFlow — the "Configure" dialog shown after setup for
                            tuning poll interval, retries, CFM alert settings, etc.

When the user completes either flow, HA stores the submitted data in the config
entry (entry.data for setup, entry.options for options) and the integration is
reloaded to pick up the new values.
"""

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
    """Handle the initial setup wizard for one Panasonic ERV device."""

    VERSION = 1  # increment this if entry.data format changes in a breaking way

    async def async_step_user(self, user_input=None) -> FlowResult:
        """Show the setup form and validate the entered URL.

        HA calls this method twice:
          - First call (user_input=None): render the empty form.
          - Second call (user_input=dict): the user submitted the form; validate
            and either show errors or create the entry.
        """
        errors: dict[str, str] = {}

        if user_input is not None:
            # Try to reach the device before saving anything.  We call
            # /api/v1/summary rather than /api/v1/state because the summary
            # also gives us the MAC address and firmware version to store.
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
                    # Setting a unique_id based on MAC prevents the same physical
                    # device from being added twice under different names/URLs.
                    await self.async_set_unique_id(mac)
                    self._abort_if_unique_id_configured()

                # Store MAC, model, and firmware alongside the user-supplied
                # values so entity.py can populate the HA device registry entry.
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
        """Tell HA that this integration supports an options flow.

        HA calls this to get the options flow handler when the user clicks
        "Configure" on the integration card.
        """
        return PanasonicERVOptionsFlow(config_entry)


class PanasonicERVOptionsFlow(config_entries.OptionsFlow):
    """Handle the options dialog shown after the integration is set up.

    Changes saved here are stored in entry.options and trigger an entry
    reload so the coordinator picks up the new values immediately.
    """

    def __init__(self, config_entry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None) -> FlowResult:
        """Show the options form, pre-filled with current values."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        # Use current option values as defaults so the form shows what is
        # already configured rather than generic placeholder text.
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
