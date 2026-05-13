"""Coordinator for Panasonic ERV data updates."""

import asyncio
import logging
from datetime import timedelta

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import PanasonicERVApiError
from .const import (
    CONF_BOOST_RECOVERY,
    CONF_POLL_INTERVAL,
    CONF_RETRY_COUNT,
    CONF_VERIFY_DELAY,
    DEFAULT_BOOST_RECOVERY,
    DEFAULT_POLL_INTERVAL,
    DEFAULT_RETRY_COUNT,
    DEFAULT_VERIFY_DELAY,
)

_LOGGER = logging.getLogger(__name__)


class PanasonicERVDataUpdateCoordinator(DataUpdateCoordinator):
    """Manages polling and command dispatch for the ERV."""

    def __init__(self, hass, api_client, entry) -> None:
        options = entry.options
        self.api_client = api_client
        self.entry = entry
        self._retry_count: int = int(
            options.get(CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT)
        )
        self._verify_delay: int = int(
            options.get(CONF_VERIFY_DELAY, DEFAULT_VERIFY_DELAY)
        )
        self._boost_recovery: bool = options.get(
            CONF_BOOST_RECOVERY, DEFAULT_BOOST_RECOVERY
        )
        self.desired_boost: bool | None = None
        self.desired_speed: str | None = None
        self.device_config: dict = {}

        super().__init__(
            hass,
            logger=_LOGGER,
            name=entry.data.get("device_name", "Panasonic ERV"),
            update_interval=timedelta(
                seconds=int(
                    options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL)
                )
            ),
        )

    async def _async_update_data(self) -> dict:
        data = await self._fetch_with_retry(self.api_client.async_get_state)

        try:
            self.device_config = await self._fetch_with_retry(
                self.api_client.async_get_device_config
            )
        except Exception:
            pass

        if self._boost_recovery and self.desired_boost is True:
            try:
                boost_mode = data["host"]["components"]["0"]["boost"]["mode"]
            except (KeyError, TypeError):
                boost_mode = "off"
            if boost_mode != "on":
                _LOGGER.debug("Boost expired on device; resending boost command")
                try:
                    await self.api_client.async_set_boost(True)
                    await asyncio.sleep(self._verify_delay)
                    data = await self._fetch_with_retry(self.api_client.async_get_state)
                except PanasonicERVApiError as err:
                    _LOGGER.warning("Boost recovery failed: %s", err)

        if self._boost_recovery and self.desired_speed is not None:
            try:
                current_speed = data["host"]["components"]["0"]["speed"]
            except (KeyError, TypeError):
                current_speed = None
            if current_speed is not None and current_speed != self.desired_speed:
                _LOGGER.debug(
                    "Speed mismatch (desired: %s, actual: %s); resending",
                    self.desired_speed,
                    current_speed,
                )
                try:
                    await self.api_client.async_set_speed(self.desired_speed)
                    await asyncio.sleep(self._verify_delay)
                    data = await self._fetch_with_retry(self.api_client.async_get_state)
                except PanasonicERVApiError as err:
                    _LOGGER.warning("Speed recovery failed: %s", err)

        return data

    async def _fetch_with_retry(self, coro_fn) -> dict:
        """Call coro_fn(), retrying up to _retry_count times on API errors."""
        last_err: Exception | None = None
        for attempt in range(self._retry_count):
            try:
                return await coro_fn()
            except PanasonicERVApiError as err:
                last_err = err
                if attempt < self._retry_count - 1:
                    await asyncio.sleep(1)
        raise UpdateFailed(last_err)

    async def async_send_command(self, coro_fn) -> None:
        """Send a command with retries, then verify state after the configured delay."""
        last_err: Exception | None = None
        for attempt in range(self._retry_count):
            try:
                await coro_fn()
                last_err = None
                break
            except PanasonicERVApiError as err:
                last_err = err
                if attempt < self._retry_count - 1:
                    await asyncio.sleep(1)

        if last_err is not None:
            raise HomeAssistantError(
                f"Command failed after {self._retry_count} attempts: {last_err}"
            )

        await asyncio.sleep(self._verify_delay)
        await self.async_request_refresh()
