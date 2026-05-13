"""Panasonic ERV API client."""

import asyncio
from aiohttp import ClientError


class PanasonicERVApiError(Exception):
    """An error occurred while talking to the Panasonic ERV."""


class PanasonicERVApi:
    """Simple wrapper for Panasonic ERV HTTP calls."""

    def __init__(self, session, device_url: str) -> None:
        self._session = session
        self._device_url = device_url.rstrip("/")

    async def _request(self, method: str, path: str, **kwargs) -> dict:
        url = f"{self._device_url}{path}"
        try:
            async with asyncio.timeout(10):
                response = await self._session.request(method, url, **kwargs)
                response.raise_for_status()
                return await response.json()
        except (ClientError, asyncio.TimeoutError) as err:
            raise PanasonicERVApiError(err) from err

    async def async_get_state(self) -> dict:
        return await self._request("GET", "/api/v1/state")

    async def async_get_summary(self) -> dict:
        return await self._request("GET", "/api/v1/summary")

    async def async_get_device_config(self) -> dict:
        return await self._request("GET", "/api/v1/device_config")

    async def async_post_command(self, payload: dict) -> dict:
        return await self._request("POST", "/api/v1/command", json=payload)

    async def async_post_device_config(self, payload: dict) -> dict:
        return await self._request("POST", "/api/v1/device_config", json=payload)

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
        return await self.async_post_device_config(
            {"host": {"components": {"0": {key: value}}}}
        )
