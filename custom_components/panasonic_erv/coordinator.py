"""Data update coordinator for the Panasonic ERV integration.

The coordinator is the heart of the integration.  Home Assistant's
DataUpdateCoordinator pattern works like this:

  1. The coordinator polls the device on a timer (_async_update_data).
  2. It stores the result in self.data.
  3. All entities subscribe to the coordinator.  When new data arrives, every
     entity is notified and re-renders itself from self.data — no entity ever
     calls the API directly for reads.

This keeps all network I/O in one place, ensures the device is only polled
once per interval regardless of how many entities exist, and gives every entity
a consistent view of the device state.

Beyond basic polling, this coordinator also handles:
  - Retry logic: failed reads and writes are retried before raising an error.
  - Command verification: after a write, it waits and re-polls to confirm.
  - Desired-state recovery: if boost or speed drifts from what HA last set
    (e.g. boost expires after ~1 hour, or a power cycle resets speed), the
    coordinator automatically resends the last commanded value.
  - Device config: fetches /api/v1/device_config alongside the runtime state
    so number and select entities can read configuration values.
"""

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
    """Manages polling, retries, and desired-state recovery for one ERV device."""

    def __init__(self, hass, api_client, entry) -> None:
        # Pull tunable values from the options the user configured (or defaults
        # if they have never opened the options flow).
        options = entry.options
        self.api_client = api_client
        self.entry = entry  # stored so entities can read entry.data / entry.options
        self._retry_count: int = int(
            options.get(CONF_RETRY_COUNT, DEFAULT_RETRY_COUNT)
        )
        self._verify_delay: int = int(
            options.get(CONF_VERIFY_DELAY, DEFAULT_VERIFY_DELAY)
        )
        self._boost_recovery: bool = options.get(
            CONF_BOOST_RECOVERY, DEFAULT_BOOST_RECOVERY
        )

        # Desired-state tracking.  These are set by the entity when the user
        # issues a command, and cleared only if the user explicitly turns the
        # feature off.  The recovery logic below uses them to detect drift.
        self.desired_boost: bool | None = None
        self.desired_speed: str | None = None

        # Device config is fetched alongside runtime state each poll cycle and
        # stored here so number/select entities can read it without an extra
        # API call.  Starts empty; entities handle the not-yet-loaded case.
        self.device_config: dict = {}

        super().__init__(
            hass,
            logger=_LOGGER,
            name=entry.data.get("device_name", "Panasonic ERV"),
            update_interval=timedelta(
                seconds=int(options.get(CONF_POLL_INTERVAL, DEFAULT_POLL_INTERVAL))
            ),
        )

    async def _async_update_data(self) -> dict:
        """Fetch fresh state from the device and run recovery checks.

        Called automatically by the base class on every poll interval, and also
        triggered manually after a command via async_request_refresh().
        """
        # Fetch runtime state with retry.  This is the primary data that all
        # entities use; if it fails after all retries, the update is marked
        # failed and entities show as unavailable.
        data = await self._fetch_with_retry(self.api_client.async_get_state)

        # Fetch device config alongside runtime state.  This is best-effort —
        # a failure here does NOT fail the whole update, it just leaves
        # self.device_config at its last known value (or empty on first run).
        try:
            self.device_config = await self._fetch_with_retry(
                self.api_client.async_get_device_config
            )
        except Exception:  # noqa: BLE001
            pass

        # --- Boost recovery ---
        # Boost mode has a hardware timer that resets it after roughly 1 hour.
        # If the user turned boost on in HA and the device has since turned it
        # off on its own, resend the command automatically.
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

        # --- Speed recovery ---
        # Speed could drift after a power cycle or external change.  If HA has
        # a desired speed recorded and the device disagrees, resend it.
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
        """Call coro_fn() and retry up to _retry_count times on API errors.

        A 1-second pause between attempts gives the device time to recover from
        transient issues (e.g. Wi-Fi congestion).  If all attempts fail, raises
        UpdateFailed which HA uses to mark entities as unavailable.
        """
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
        """Send a device command with retries, then verify the result.

        Entity write methods (turn_on, async_select_option, etc.) call this
        instead of the API directly so retry and verification logic is in one
        place.

        Flow:
          1. Call coro_fn() — the actual API write.
          2. Retry up to _retry_count times if it fails.
          3. Wait _verify_delay seconds to give the device time to apply the change.
          4. Trigger a state refresh so entities immediately reflect the new state.

        Raises HomeAssistantError (shown as a notification in the HA UI) if all
        retries are exhausted.
        """
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

        # Short pause then re-poll so the UI updates promptly after a command.
        await asyncio.sleep(self._verify_delay)
        await self.async_request_refresh()
