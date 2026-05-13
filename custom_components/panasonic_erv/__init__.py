"""Panasonic ERV integration."""

from __future__ import annotations

import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import aiohttp_client

from .api import PanasonicERVApi
from .const import (
    CONF_DEVICE_NAME,
    CONF_DEVICE_URL,
    CONF_POLL_INTERVAL,
    DEFAULT_POLL_INTERVAL,
    DATA_COORDINATOR,
    DOMAIN,
)
from .coordinator import PanasonicERVDataUpdateCoordinator

PLATFORMS = ["switch", "select", "sensor", "binary_sensor"]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Panasonic ERV integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry."""
    session = aiohttp_client.async_get_clientsession(hass)
    api = PanasonicERVApi(session, entry.data[CONF_DEVICE_URL])
    update_interval = entry.options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
    coordinator = PanasonicERVDataUpdateCoordinator(
        hass, api, update_interval, entry.data[CONF_DEVICE_NAME]
    )

    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {DATA_COORDINATOR: coordinator}

    for platform in PLATFORMS:
        await hass.config_entries.async_forward_entry_setup(entry, platform)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, platform)
                for platform in PLATFORMS
            ]
        )
    )

    if unload_ok and entry.entry_id in hass.data.get(DOMAIN, {}):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
