"""Number entities for Panasonic ERV device configuration.

These entities expose the numeric settings stored in /api/v1/device_config —
things like CFM limits for each speed, runtime duration, and humidity/temperature
thresholds.  They are backed by coordinator.device_config (fetched alongside
the runtime state each poll cycle) and write through coordinator.async_send_command
via async_set_device_config.

All entities are disabled by default.  This is intentional: these are rarely
changed settings that most users will never touch.  Enabling individual entities
in the HA UI makes them visible and interactive without cluttering the default
device card with 14 extra controls.

Enabling an entity immediately shows the current value from device_config.
Nothing is sent to the device until you explicitly change the value.

Note: The meanings of some fields (runtime, defaultTimer) are not fully
confirmed from device experimentation.  Use caution when changing them until
their behaviour is better understood.
"""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .entity import PanasonicERVEntity

# Each entry describes one number entity:
#   (suffix, display_name, device_config_key, min, max, step, unit, icon, mode)
#
# device_config_key is the exact key name in the host.components.0 object
# of the /api/v1/device_config response.
#
# step=1 causes the value to be written as an integer rather than a float,
# matching the integer format the device expects for these fields.
_NUMBER_DESCRIPTIONS = [
    (
        "cfg_low_sa",
        "Low Speed Supply CFM",
        "lowSa",
        0, 120, 1,
        "CFM",
        "mdi:arrow-up-bold-circle-outline",
        NumberMode.BOX,
    ),
    (
        "cfg_low_ea",
        "Low Speed Exhaust CFM",
        "lowEa",
        0, 120, 1,
        "CFM",
        "mdi:arrow-down-bold-circle-outline",
        NumberMode.BOX,
    ),
    (
        "cfg_high_sa",
        "High Speed Supply CFM",
        "highSa",
        0, 120, 1,
        "CFM",
        "mdi:arrow-up-bold-circle-outline",
        NumberMode.BOX,
    ),
    (
        "cfg_high_ea",
        "High Speed Exhaust CFM",
        "highEa",
        0, 120, 1,
        "CFM",
        "mdi:arrow-down-bold-circle-outline",
        NumberMode.BOX,
    ),
    (
        "cfg_boost_sa",
        "Boost Supply CFM",
        "boostSa",
        0, 120, 1,
        "CFM",
        "mdi:arrow-up-bold-circle-outline",
        NumberMode.BOX,
    ),
    (
        "cfg_boost_ea",
        "Boost Exhaust CFM",
        "boostEa",
        0, 120, 1,
        "CFM",
        "mdi:arrow-down-bold-circle-outline",
        NumberMode.BOX,
    ),
    (
        "cfg_runtime",
        "Runtime",          # exact meaning not yet confirmed from device testing
        "runtime",
        0, 480, 1,
        UnitOfTime.MINUTES,
        "mdi:timer-outline",
        NumberMode.BOX,
    ),
    (
        "cfg_humidity_control_setting",
        "Humidity Control Setpoint",
        "humidityControlSetting",
        0, 100, 1,
        PERCENTAGE,
        "mdi:water-percent",
        NumberMode.SLIDER,
    ),
    (
        "cfg_high_humidity_threshold",
        "High Humidity Threshold",
        "highHumidityThreshold",
        0, 100, 1,
        PERCENTAGE,
        "mdi:water-percent",
        NumberMode.SLIDER,
    ),
    (
        "cfg_low_temp_threshold",
        "Low Temperature Threshold",
        "lowTempThreshold",
        -30, 30, 1,
        UnitOfTemperature.CELSIUS,
        "mdi:thermometer-low",
        NumberMode.BOX,
    ),
    (
        "cfg_supply_limit_low_temp",
        "Supply Limit Low Temp",    # 0 or 1 flag; exact behaviour not yet confirmed
        "supplyLimitLowTemp",
        0, 1, 1,
        None,
        "mdi:thermometer-minus",
        NumberMode.BOX,
    ),
    (
        "cfg_supply_limit_high_hum",
        "Supply Limit High Humidity",  # 0 or 1 flag; exact behaviour not yet confirmed
        "supplyLimitHighHum",
        0, 1, 1,
        None,
        "mdi:water-percent",
        NumberMode.BOX,
    ),
    (
        "cfg_log_rate",
        "Log Rate",
        "log_rate",
        60000, 3600000, 1000,
        UnitOfTime.MILLISECONDS,
        "mdi:clipboard-clock-outline",
        NumberMode.BOX,
    ),
    (
        "cfg_offset",
        "Balancing Offset",
        "offset",
        -10, 10, 1,
        "CFM",
        "mdi:scale-balance",
        NumberMode.BOX,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create one number entity per row in _NUMBER_DESCRIPTIONS."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        [
            PanasonicERVNumber(
                coordinator, suffix, name, config_key,
                min_val, max_val, step, unit, icon, mode,
            )
            for suffix, name, config_key, min_val, max_val, step, unit, icon, mode
            in _NUMBER_DESCRIPTIONS
        ]
    )


class PanasonicERVNumber(PanasonicERVEntity, NumberEntity):
    """A number entity backed by a single field in /api/v1/device_config."""

    def __init__(
        self,
        coordinator,
        suffix: str,
        name: str,
        config_key: str,
        min_val: float,
        max_val: float,
        step: float,
        unit,
        icon: str,
        mode: NumberMode,
    ) -> None:
        super().__init__(coordinator, suffix)
        self._attr_name = name
        self._config_key = config_key  # key in host.components.0 of device_config
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_mode = mode
        # Disabled by default — enable individually via the HA entity settings UI.
        self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self) -> float | None:
        """Read the current value from the coordinator's cached device_config."""
        try:
            return self.coordinator.device_config["host"]["components"]["0"][
                self._config_key
            ]
        except (KeyError, TypeError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        """Write the new value to the device via device_config.

        The device expects integer values for all fields with step=1, so we
        cast to int before sending to avoid sending "65.0" instead of "65".
        """
        int_value = int(value) if self._attr_native_step == 1 else value
        await self.coordinator.async_send_command(
            lambda: self.coordinator.api_client.async_set_device_config(
                self._config_key, int_value
            )
        )
