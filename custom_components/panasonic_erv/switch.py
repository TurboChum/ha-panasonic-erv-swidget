"""Panasonic ERV switch entities."""

from homeassistant.components.switch import SwitchEntity

from .const import DOMAIN

class PanasonicERVPowerSwitch(SwitchEntity):
    """Power switch for the Panasonic ERV."""

    def __init__(self, coordinator, name):
        self.coordinator = coordinator
        self._name = name

    @property
    def name(self):
        return f"{self._name} Power"

    @property
    def is_on(self):
        return self.coordinator.data["host"]["components"]["0"]["toggle"]["state"] == "on"

    async def async_turn_on(self, **kwargs):
        await self.coordinator.api_client.async_set_power(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.api_client.async_set_power(False)
        await self.coordinator.async_request_refresh()
