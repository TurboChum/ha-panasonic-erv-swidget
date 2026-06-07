"""Switch entities for the Panasonic ERV integration.

Exposes three on/off controls:
  - Power       — turns the ERV on or off (toggle.state)
  - Boost       — enables high-flow boost mode for ~1 hour (boost.mode)
  - Auto Runtime — enables the device's built-in auto-runtime scheduler
                   (device_config autoRuntime: 0=off, 1=on)

Power and Boost read from coordinator.data (runtime state).
Auto Runtime reads from coordinator.device_config and is disabled by default —
enable it via the entity settings UI if you use the auto-runtime feature.

All write commands route through coordinator.async_send_command so retry logic,
the verification delay, and state recovery are handled in one place.
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
            PanasonicERVAutoRuntimeSwitch(coordinator),
            PanasonicERVIntermittentModeSwitch(coordinator),
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
        """Return True if the ERV is currently running.

        Reuses the base-class _is_powered_on helper, which guards against a
        missing/partial payload (returns False instead of raising) so a malformed
        poll response doesn't spam the log with KeyErrors.
        """
        return self._is_powered_on

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
    def available(self) -> bool:
        return self.coordinator.last_update_success and self._is_powered_on

    @property
    def is_on(self) -> bool | None:
        """Return True if boost mode is currently active.

        Returns None (unknown) rather than raising if the payload is missing the
        boost field, matching the defensive reads used elsewhere.
        """
        try:
            return (
                self.coordinator.data["host"]["components"]["0"]["boost"]["mode"] == "on"
            )
        except (KeyError, TypeError):
            return None

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


class PanasonicERVAutoRuntimeSwitch(PanasonicERVEntity, SwitchEntity):
    """Enables or disables the device's built-in auto-runtime scheduler.

    Reads from coordinator.device_config (autoRuntime: 0=off, 1=on).
    Disabled by default — enable via the HA entity settings UI if needed.
    Unavailable until device_config has been fetched for the first time.
    """

    _attr_name = "Auto Runtime"
    _attr_icon = "mdi:timer-play-outline"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "auto_runtime")

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and bool(self.coordinator.device_config)

    @property
    def is_on(self) -> bool | None:
        try:
            value = self.coordinator.device_config["host"]["components"]["0"]["autoRuntime"]
            return bool(value)
        except (KeyError, TypeError):
            return None

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_send_command(
            lambda: self.coordinator.api_client.async_set_device_config("autoRuntime", 1)
        )

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_send_command(
            lambda: self.coordinator.api_client.async_set_device_config("autoRuntime", 0)
        )


class PanasonicERVIntermittentModeSwitch(PanasonicERVEntity, SwitchEntity):
    """Enables or disables intermittent (duty-cycle) ventilation mode.

    When on, the ERV runs for a set period (controlled by the Runtime number
    entity) rather than continuously.  Works in conjunction with autoRuntime
    and the runtime/defaultTimer device config values.

    Reads from coordinator.device_config (intermittentMode: 0=off, 1=on).
    Disabled by default — enable via the HA entity settings UI if needed.
    Unavailable until device_config has been fetched for the first time.
    """

    _attr_name = "Intermittent Mode"
    _attr_icon = "mdi:timer-pause-outline"
    _attr_entity_registry_enabled_default = False

    def __init__(self, coordinator) -> None:
        super().__init__(coordinator, "intermittent_mode")

    @property
    def available(self) -> bool:
        return self.coordinator.last_update_success and bool(self.coordinator.device_config)

    @property
    def is_on(self) -> bool | None:
        try:
            value = self.coordinator.device_config["host"]["components"]["0"]["intermittentMode"]
            return bool(value)
        except (KeyError, TypeError):
            return None

    async def async_turn_on(self, **kwargs) -> None:
        await self.coordinator.async_send_command(
            lambda: self.coordinator.api_client.async_set_device_config("intermittentMode", 1)
        )

    async def async_turn_off(self, **kwargs) -> None:
        await self.coordinator.async_send_command(
            lambda: self.coordinator.api_client.async_set_device_config("intermittentMode", 0)
        )
