"""Panasonic ERV integration."""

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

PLATFORMS = ["switch", "select", "sensor", "binary_sensor", "number"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    session = aiohttp_client.async_get_clientsession(hass)
    api = PanasonicERVApi(session, entry.data[CONF_DEVICE_URL])
    coordinator = PanasonicERVDataUpdateCoordinator(hass, api, entry)

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {DATA_COORDINATOR: coordinator}

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    return unload_ok


async def _async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the entry when options change."""
    await hass.config_entries.async_reload(entry.entry_id)
