"""Panasonic ERV select entities."""

from homeassistant.components.select import SelectEntity
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
            PanasonicERVModeSelect(coordinator),
            PanasonicERVSpeedSelect(coordinator),
            PanasonicERVBalancingSelect(coordinator),
        ]
    )


class PanasonicERVModeSelect(PanasonicERVEntity, SelectEntity):
    """Select entity for ERV ventilation mode."""

    _attr_name = "Mode"
    _attr_icon = "mdi:cog-refresh"
    _attr_options = ["heatExchange", "supply", "exhaust", "recirculation"]

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "mode")

    @property
    def current_option(self) -> str | None:
        return self.coordinator.data["host"]["components"]["0"].get("mode")

    async def async_select_option(self, option: str) -> None:
        await self.coordinator.async_send_command(
            lambda: self.coordinator.api_client.async_set_mode(option)
        )


class PanasonicERVSpeedSelect(PanasonicERVEntity, SelectEntity):
    """Select entity for ERV fan speed."""

    _attr_name = "Speed"
    _attr_icon = "mdi:speedometer"
    _attr_options = ["low", "high"]

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "speed")

    @property
    def current_option(self) -> str | None:
        return self.coordinator.data["host"]["components"]["0"].get("speed")

    async def async_select_option(self, option: str) -> None:
        self.coordinator.desired_speed = option
        await self.coordinator.async_send_command(
            lambda: self.coordinator.api_client.async_set_speed(option)
        )


class PanasonicERVBalancingSelect(PanasonicERVEntity, SelectEntity):
    """Select entity for auto-balancing supply/exhaust CFM.

    0 = manual (no auto-balance)
    1 = auto (if supply or exhaust is restricted, proportionally slow the other side)
    """

    _attr_name = "Balancing"
    _attr_icon = "mdi:scale-balance"
    _attr_options = ["manual", "auto"]
    _attr_entity_registry_enabled_default = False

    _OPTION_TO_INT = {"manual": 0, "auto": 1}
    _INT_TO_OPTION = {0: "manual", 1: "auto"}

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "balancing")

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and bool(self.coordinator.device_config)

    @property
    def current_option(self) -> str | None:
        try:
            value = self.coordinator.device_config["host"]["components"]["0"]["balancing"]
            return self._INT_TO_OPTION.get(value)
        except (KeyError, TypeError):
            return None

    async def async_select_option(self, option: str) -> None:
        value = self._OPTION_TO_INT[option]
        await self.coordinator.async_send_command(
            lambda: self.coordinator.api_client.async_set_device_config("balancing", value)
        )
