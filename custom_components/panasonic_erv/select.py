"""Select entities for the Panasonic ERV integration.

Exposes three dropdown controls:

  Mode      — ventilation mode: Heat Exchange, Supply, Exhaust, Recirculation.
  Speed     — fan speed: Low or High.
  Balancing — whether to automatically balance supply/exhaust CFM (config entity).

Mode and Speed are runtime controls backed by /api/v1/command.
Balancing is a configuration control backed by /api/v1/device_config and is
disabled by default — enable it in the entity settings if you want to change it.
"""

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
    """Create select entities for this config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        [
            PanasonicERVModeSelect(coordinator),
            PanasonicERVSpeedSelect(coordinator),
            PanasonicERVBalancingSelect(coordinator),
        ]
    )


class PanasonicERVModeSelect(PanasonicERVEntity, SelectEntity):
    """Selects the ventilation mode.

    heatExchange  — recovers heat/cool energy from exhaust air while ventilating.
    supply        — brings in outside air only.
    exhaust       — expels indoor air only.
    recirculation — recirculates indoor air without exchanging with outside.
    """

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
    """Selects the fan speed (low or high).

    When the user picks a speed we also record it on the coordinator as the
    desired speed.  If the device ever reports a different speed on a future
    poll (e.g. after a power cycle), the coordinator will resend this value
    automatically.
    """

    _attr_name = "Speed"
    _attr_icon = "mdi:speedometer"
    _attr_options = ["low", "high"]

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "speed")

    @property
    def current_option(self) -> str | None:
        return self.coordinator.data["host"]["components"]["0"].get("speed")

    async def async_select_option(self, option: str) -> None:
        # Record intent before sending — the coordinator uses this for recovery.
        self.coordinator.desired_speed = option
        await self.coordinator.async_send_command(
            lambda: self.coordinator.api_client.async_set_speed(option)
        )


class PanasonicERVBalancingSelect(PanasonicERVEntity, SelectEntity):
    """Controls the auto-balancing feature stored in device_config.

    When auto-balancing is enabled ("auto"), the device proportionally slows
    whichever side (supply or exhaust) is not restricted, keeping the two
    airflows in balance even if one duct is partially blocked.

    The API stores this as an integer (0 = manual, 1 = auto), so this entity
    maps between those integers and human-readable option strings.

    Disabled by default — enable the entity if you want to change this setting.
    The entity will always show the current value from device_config even before
    you enable it; enabling just makes it interactive.
    """

    _attr_name = "Balancing"
    _attr_icon = "mdi:scale-balance"
    _attr_options = ["manual", "auto"]
    _attr_entity_registry_enabled_default = False  # rarely changed; hide until needed

    # Mapping between the human-readable option strings and the integer values
    # the device API uses.
    _OPTION_TO_INT = {"manual": 0, "auto": 1}
    _INT_TO_OPTION = {0: "manual", 1: "auto"}

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "balancing")

    @property
    def available(self) -> bool:
        """Only available once device_config has been fetched at least once."""
        return self.coordinator.last_update_success and bool(self.coordinator.device_config)

    @property
    def current_option(self) -> str | None:
        """Read the current balancing setting from device_config."""
        try:
            value = self.coordinator.device_config["host"]["components"]["0"]["balancing"]
            return self._INT_TO_OPTION.get(value)
        except (KeyError, TypeError):
            return None

    async def async_select_option(self, option: str) -> None:
        """Write the selected option as its integer equivalent to device_config."""
        value = self._OPTION_TO_INT[option]
        await self.coordinator.async_send_command(
            lambda: self.coordinator.api_client.async_set_device_config("balancing", value)
        )
