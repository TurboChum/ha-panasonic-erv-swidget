"""Panasonic ERV integration."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers.typing import ConfigType

DOMAIN = "panasonic_erv"

async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the Panasonic ERV integration."""
    return True

async def async_setup_entry(hass: HomeAssistant, entry) -> bool:
    """Set up a config entry."""
    return True

async def async_unload_entry(hass: HomeAssistant, entry) -> bool:
    """Unload a config entry."""
    return True
