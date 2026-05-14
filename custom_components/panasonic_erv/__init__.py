"""Panasonic ERV integration entry point.

This file is loaded by HA when the integration is set up.  Its two main jobs
are async_setup_entry (called when a config entry is created or HA restarts)
and async_unload_entry (called when the user removes the integration or HA
is shutting down).

A "config entry" is HA's term for one configured instance of an integration —
in our case, one physical ERV device.  All per-device state is stored on the
entry and keyed by entry.entry_id in hass.data[DOMAIN].
"""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .api import PanasonicERVApi
from .const import (
    CONF_DEVICE_URL,
    DATA_COORDINATOR,
    DOMAIN,
)
from .coordinator import PanasonicERVDataUpdateCoordinator

# The list of HA entity platforms this integration provides.  HA will load
# each platform's async_setup_entry function when the config entry is set up.
PLATFORMS = ["switch", "select", "sensor", "binary_sensor", "number"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up one ERV device from a config entry.

    Called once per config entry on every HA start, and again after the entry
    is reloaded (e.g. when the user changes options).

    Steps:
      1. Create a shared HTTP session and API client.
      2. Create the coordinator and do the first data fetch — if the device is
         unreachable at startup, HA will retry later automatically.
      3. Register the coordinator in hass.data so entity platforms can find it.
      4. Forward setup to each platform (switch, sensor, etc.).
      5. Register a listener to reload the entry when options change.
    """
    session = aiohttp_client.async_get_clientsession(hass)
    api = PanasonicERVApi(session, entry.data[CONF_DEVICE_URL])
    coordinator = PanasonicERVDataUpdateCoordinator(hass, api, entry)

    # Fetch initial data before any entities are created.  If this raises,
    # HA will display a setup error and retry — entities won't be created yet.
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {DATA_COORDINATOR: coordinator}

    # Forward setup to all platforms.  async_forward_entry_setups (plural) is
    # the modern HA API that sets up all platforms in a single call.
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # When the user saves new options, reload the entire entry so the
    # coordinator picks up the changed poll interval, retry count, etc.
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Tear down one ERV device config entry.

    Called when the user removes the integration or HA is shutting down.
    Unloads all entity platforms first, then removes the coordinator from
    hass.data to free memory.
    """
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when the user saves new options.

    The reload triggers async_unload_entry followed by async_setup_entry,
    which re-creates the coordinator with the updated settings.
    """
    await hass.config_entries.async_reload(entry.entry_id)
