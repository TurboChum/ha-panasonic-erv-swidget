"""Panasonic ERV select entities."""

from homeassistant.components.select import SelectEntity

class PanasonicERVModeSelect(SelectEntity):
    """Select entity for ERV mode."""

    def __init__(self, coordinator, name):
        self.coordinator = coordinator
        self._name = name
        self._options = ["heatExchange", "supply", "exhaust", "recirculation"]

    @property
    def name(self):
        return f"{self._name} Mode"

    @property
    def current_option(self):
        return self.coordinator.data["host"]["components"]["0"]["mode"]

    @property
    def options(self):
        return self._options

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.api_client.async_set_mode(option)
        await self.coordinator.async_request_refresh()
