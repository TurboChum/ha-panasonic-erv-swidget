"""Coordinator for Panasonic ERV data updates."""

from datetime import timedelta

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_POLL_INTERVAL

class PanasonicERVDataUpdateCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from the ERV."""

    def __init__(self, hass, api_client):
        super().__init__(
            hass,
            logger=None,
            name="panasonic_erv",
            update_interval=timedelta(seconds=DEFAULT_POLL_INTERVAL),
        )
        self.api_client = api_client

    async def _async_update_data(self):
        try:
            return await self.api_client.async_get_state()
        except Exception as err:
            raise UpdateFailed(err)
