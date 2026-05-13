"""Panasonic ERV API client."""

import asyncio
import async_timeout
from aiohttp import ClientError


class PanasonicERVApiError(Exception):
    """An error occurred while talking to the Panasonic ERV."""


class PanasonicERVApi:
    """Simple wrapper for Panasonic ERV HTTP calls."""

    def __init__(self, session, device_url: str) -> None:
        self._session = session
        self._device_url = device_url.rstrip("/")

    async def async_get_state(self) -> dict:
        url = f"{self._device_url}/api/v1/state"
        try:
            async with async_timeout.timeout(10):
                response = await self._session.get(url)
                response.raise_for_status()
                return await response.json()
        except (ClientError, asyncio.TimeoutError) as err:
            raise PanasonicERVApiError(err)

    async def async_post_command(self, payload: dict) -> dict:
        url = f"{self._device_url}/api/v1/command"
        try:
            async with async_timeout.timeout(10):
                response = await self._session.post(url, json=payload)
                response.raise_for_status()
                return await response.json()
        except (ClientError, asyncio.TimeoutError) as err:
            raise PanasonicERVApiError(err)

    async def async_set_mode(self, mode: str) -> dict:
        payload = {"host": {"components": {"0": {"mode": mode}}}}
        return await self.async_post_command(payload)

    async def async_set_power(self, power_on: bool) -> dict:
        state = "on" if power_on else "off"
        payload = {"host": {"components": {"0": {"toggle": {"state": state}}}}}
        return await self.async_post_command(payload)

    async def async_set_speed(self, speed: str) -> dict:
        payload = {"host": {"components": {"0": {"speed": speed}}}}
        return await self.async_post_command(payload)

    async def async_set_boost(self, boost_on: bool) -> dict:
        mode = "on" if boost_on else "off"
        payload = {"host": {"components": {"0": {"boost": {"mode": mode}}}}}
        return await self.async_post_command(payload)
