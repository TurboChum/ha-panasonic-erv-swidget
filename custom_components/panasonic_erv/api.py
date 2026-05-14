"""HTTP API client for the Panasonic ERV / Swidget device.

This module is the only place in the integration that talks to the device over
the network.  Every other module calls methods on PanasonicERVApi instead of
making HTTP requests directly, which keeps networking concerns in one place and
makes the rest of the code easier to test.

The device exposes a simple JSON-over-HTTP API with no authentication:
  GET  /api/v1/state         — live runtime values (temperature, CFM, mode, …)
  GET  /api/v1/summary       — static device info (MAC, model, firmware version)
  GET  /api/v1/device_config — stored configuration (CFM limits, thresholds, …)
  POST /api/v1/command       — send a runtime control command
  POST /api/v1/device_config — write one or more configuration fields

All response values of interest live under host.components.0 in the JSON tree.
"""

import asyncio
from aiohttp import ClientError


class PanasonicERVApiError(Exception):
    """Raised whenever a network request to the device fails.

    Wrapping all aiohttp and timeout errors in a single type means callers only
    need to catch one exception class regardless of what went wrong at the
    transport layer.
    """


class PanasonicERVApi:
    """Thin wrapper around the Swidget HTTP endpoints.

    Accepts a shared aiohttp ClientSession (provided by HA via
    aiohttp_client.async_get_clientsession) so that connections are reused
    across requests rather than opening a new socket every poll cycle.
    """

    def __init__(self, session, device_url: str) -> None:
        self._session = session
        # Strip a trailing slash so every path can start with "/" without
        # accidentally producing double-slashes in the URL.
        self._device_url = device_url.rstrip("/")

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        """Make a single HTTP request and return the parsed JSON response.

        The 10-second timeout covers slow Wi-Fi or a busy device.  Any network
        or HTTP error is re-raised as PanasonicERVApiError so callers get a
        consistent exception type to catch.
        """
        url = f"{self._device_url}{path}"
        try:
            async with asyncio.timeout(10):
                response = await self._session.request(method, url, **kwargs)
                response.raise_for_status()  # turns 4xx/5xx into an exception
                return await response.json()
        except (ClientError, asyncio.TimeoutError) as err:
            raise PanasonicERVApiError(err) from err

    # --- Read endpoints ---

    async def async_get_state(self) -> dict:
        """Fetch the live runtime state (temperature, CFM, mode, speed, …)."""
        return await self._request("GET", "/api/v1/state")

    async def async_get_summary(self) -> dict:
        """Fetch static device info (MAC address, model type, firmware version).

        Called once during integration setup to validate connectivity and
        capture the MAC address used as the stable device identifier.
        """
        return await self._request("GET", "/api/v1/summary")

    async def async_get_device_config(self) -> dict:
        """Fetch stored device configuration (CFM limits, thresholds, etc.)."""
        return await self._request("GET", "/api/v1/device_config")

    # --- Write endpoints ---

    async def async_post_command(self, payload: dict) -> dict:
        """POST a runtime command payload to the device.

        The device expects partial updates — only the keys you want to change
        need to be included.  Unspecified fields are left unchanged.
        """
        return await self._request("POST", "/api/v1/command", json=payload)

    async def async_post_device_config(self, payload: dict) -> dict:
        """POST a device configuration update."""
        return await self._request("POST", "/api/v1/device_config", json=payload)

    # --- Convenience command helpers ---
    # Each helper builds the nested JSON structure the device expects:
    # { "host": { "components": { "0": { <field>: <value> } } } }

    async def async_set_mode(self, mode: str) -> dict:
        return await self.async_post_command(
            {"host": {"components": {"0": {"mode": mode}}}}
        )

    async def async_set_power(self, power_on: bool) -> dict:
        state = "on" if power_on else "off"
        return await self.async_post_command(
            {"host": {"components": {"0": {"toggle": {"state": state}}}}}
        )

    async def async_set_speed(self, speed: str) -> dict:
        return await self.async_post_command(
            {"host": {"components": {"0": {"speed": speed}}}}
        )

    async def async_set_boost(self, boost_on: bool) -> dict:
        mode = "on" if boost_on else "off"
        return await self.async_post_command(
            {"host": {"components": {"0": {"boost": {"mode": mode}}}}}
        )

    async def async_set_device_config(self, key: str, value) -> dict:
        """Write a single device_config field by key name."""
        return await self.async_post_device_config(
            {"host": {"components": {"0": {key: value}}}}
        )
