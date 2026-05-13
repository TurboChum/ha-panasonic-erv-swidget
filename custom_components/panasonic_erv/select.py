"""Panasonic ERV select entities."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.select import SelectEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_NAME, DATA_COORDINATOR, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up select entities for Panasonic ERV."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    device_name = entry.data[CONF_DEVICE_NAME]

    async_add_entities(
        [
            PanasonicERVModeSelect(coordinator, device_name),
            PanasonicERVSpeedSelect(coordinator, device_name),
        ],
        True,
    )


class PanasonicERVModeSelect(CoordinatorEntity, SelectEntity):
    """Select entity for ERV ventilation mode."""

    def __init__(self, coordinator, name: str) -> None:
        super().__init__(coordinator)
        self._name = name
        self._options = ["heatExchange", "supply", "exhaust", "recirculation"]

    @property
    def unique_id(self) -> str:
        return f"{self._name}_mode".lower().replace(" ", "_")

    @property
    def name(self) -> str:
        return f"{self._name} Mode"

    @property
    def current_option(self) -> str:
        return self.coordinator.data["host"]["components"]["0"]["mode"]

    @property
    def options(self) -> list[str]:
        return self._options

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.api_client.async_set_mode(option)
        await self.coordinator.async_request_refresh()


class PanasonicERVSpeedSelect(CoordinatorEntity, SelectEntity):
    """Select entity for ERV speed."""

    def __init__(self, coordinator, name: str) -> None:
        super().__init__(coordinator)
        self._name = name
        self._options = ["low", "high"]

    @property
    def unique_id(self) -> str:
        return f"{self._name}_speed".lower().replace(" ", "_")

    @property
    def name(self) -> str:
        return f"{self._name} Speed"

    @property
    def current_option(self) -> str:
        return self.coordinator.data["host"]["components"]["0"]["speed"]

    @property
    def options(self) -> list[str]:
        return self._options

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.api_client.async_set_speed(option)
        await self.coordinator.async_request_refresh()
