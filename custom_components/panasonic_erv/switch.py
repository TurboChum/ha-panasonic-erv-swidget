"""Switch entities for the Panasonic ERV integration.

Exposes two on/off controls:
  - Power  — turns the ERV on or off (toggle.state)
  - Boost  — enables high-flow boost mode for ~1 hour (boost.mode)

Both entities route their write commands through coordinator.async_send_command
so that retry logic, the verification delay, and state recovery are handled
consistently in one place.
"""

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
    """Create switch entities for this config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        [
            PanasonicERVPowerSwitch(coordinator),
            PanasonicERVBoostSwitch(coordinator),
        ]
    )


class PanasonicERVPowerSwitch(PanasonicERVEntity, SwitchEntity):
    """Controls the overall power state of the ERV (on / off)."""

    _attr_name = "Power"
    _attr_icon = "mdi:power"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "power")

    @property
    def is_on(self) -> bool:
        """Return True if the ERV is currently running."""
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
    """Controls boost mode — a high-flow override that lasts roughly 1 hour.

    When the user turns boost on, we record the desired state on the coordinator
    (desired_boost = True).  The coordinator's recovery logic checks this value
    on every poll and resends the boost command if the device has reset it —
    which happens automatically after the hardware timer expires.
    """

    _attr_name = "Boost"
    _attr_icon = "mdi:fan-plus"

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "boost")

    @property
    def is_on(self) -> bool:
        """Return True if boost mode is currently active."""
        return (
            self.coordinator.data["host"]["components"]["0"]["boost"]["mode"] == "on"
        )

    async def async_turn_on(self, **kwargs) -> None:
        # Record intent before sending — the coordinator uses this for recovery.
        self.coordinator.desired_boost = True
        await self.coordinator.async_send_command(
            lambda: self.coordinator.api_client.async_set_boost(True)
        )

    async def async_turn_off(self, **kwargs) -> None:
        # Clear intent so the coordinator stops trying to re-enable boost.
        self.coordinator.desired_boost = False
        await self.coordinator.async_send_command(
            lambda: self.coordinator.api_client.async_set_boost(False)
        )
