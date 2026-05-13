"""Panasonic ERV switch entities."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .entity import PanasonicERVEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        [
            PanasonicERVPowerSwitch(coordinator),
            PanasonicERVBoostSwitch(coordinator),
        ]
    )


class PanasonicERVPowerSwitch(PanasonicERVEntity, SwitchEntity):
    """Power switch for the Panasonic ERV."""

    _attr_name = "Power"
    _attr_icon = "mdi:power"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "power")

    @property
    def is_on(self) -> bool:
        return (
            self.coordinator.data["host"]["components"]["0"]["toggle"]["state"] == "on"
        )

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_send_command(
            lambda: self.coordinator.api_client.async_set_power(True)
        )

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_send_command(
            lambda: self.coordinator.api_client.async_set_power(False)
        )


class PanasonicERVBoostSwitch(PanasonicERVEntity, SwitchEntity):
    """Boost mode switch for the Panasonic ERV."""

    _attr_name = "Boost"
    _attr_icon = "mdi:fan-plus"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "boost")

    @property
    def is_on(self) -> bool:
        return (
            self.coordinator.data["host"]["components"]["0"]["boost"]["mode"] == "on"
        )

    async def async_turn_on(self, **kwargs) -> None:
        self.coordinator.desired_boost = True
        await self.coordinator.async_send_command(
            lambda: self.coordinator.api_client.async_set_boost(True)
        )

    async def async_turn_off(self, **kwargs) -> None:
        self.coordinator.desired_boost = False
        await self.coordinator.async_send_command(
            lambda: self.coordinator.api_client.async_set_boost(False)
        )
