"""Panasonic ERV switch entities."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_NAME, DATA_COORDINATOR, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up switch entities for Panasonic ERV."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    device_name = entry.data[CONF_DEVICE_NAME]

    async_add_entities(
        [
            PanasonicERVPowerSwitch(coordinator, device_name),
            PanasonicERVBoostSwitch(coordinator, device_name),
        ],
        True,
    )


class PanasonicERVPowerSwitch(CoordinatorEntity, SwitchEntity):
    """Power switch for the Panasonic ERV."""

    def __init__(self, coordinator, name: str) -> None:
        super().__init__(coordinator)
        self._name = name

    @property
    def unique_id(self) -> str:
        return f"{self._name}_power".lower().replace(" ", "_")

    @property
    def name(self) -> str:
        return f"{self._name} Power"

    @property
    def is_on(self) -> bool:
        return (
            self.coordinator.data["host"]["components"]["0"]["toggle"]["state"]
            == "on"
        )

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.api_client.async_set_power(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.api_client.async_set_power(False)
        await self.coordinator.async_request_refresh()


class PanasonicERVBoostSwitch(CoordinatorEntity, SwitchEntity):
    """Boost mode switch for the Panasonic ERV."""

    def __init__(self, coordinator, name: str) -> None:
        super().__init__(coordinator)
        self._name = name

    @property
    def unique_id(self) -> str:
        return f"{self._name}_boost".lower().replace(" ", "_")

    @property
    def name(self) -> str:
        return f"{self._name} Boost"

    @property
    def is_on(self) -> bool:
        return self.coordinator.data["host"]["components"]["0"]["boost"]["mode"] == "on"

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.api_client.async_set_boost(True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.api_client.async_set_boost(False)
        await self.coordinator.async_request_refresh()
