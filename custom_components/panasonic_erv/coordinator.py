"""Coordinator for Panasonic ERV data updates."""

import logging
from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_POLL_INTERVAL

_LOGGER = logging.getLogger(__name__)


class PanasonicERVDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the ERV."""

    def __init__(self, hass, api_client, update_interval: int, device_name: str):
        super().__init__(
            hass,
            logger=_LOGGER,
            name=device_name,
            update_interval=timedelta(seconds=update_interval or DEFAULT_POLL_INTERVAL),
        )
        self.api_client = api_client
        self.device_name = device_name

    async def _async_update_data(self):
        try:
            return await self.api_client.async_get_state()
        except Exception as err:
            raise UpdateFailed(err)
