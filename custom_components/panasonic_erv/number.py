"""Number entities for Panasonic ERV device configuration.

These entities expose the numeric settings stored in /api/v1/device_config —
things like CFM limits for each speed, runtime duration, and humidity/temperature
thresholds.  They are backed by coordinator.device_config (fetched alongside
the runtime state each poll cycle) and write through coordinator.async_send_command
via async_set_device_config.

All entities are disabled by default.  This is intentional: these are rarely
changed settings that most users will never touch.  Enabling individual entities
in the HA UI makes them visible and interactive without cluttering the default
device card with extra controls.

Enabling an entity immediately shows the current value from device_config.
Nothing is sent to the device until you explicitly change the value.

CFM entities (PanasonicERVCFMNumber) have dynamic min/max bounds:
  - Minimum is always 30 CFM.
  - Maximum is read live from the device's reported capability
    (state["host"]["components"]["0"][direction]["allowed"][1]).
    This differs between installations (100, 120, 150 CFM units, etc.)
  - A 10 CFM gap is enforced between speed tiers in the same direction:
      low max  = current high value  - 10
      high max = current boost value - 10
      boost max = device reported max
    Supply and exhaust are evaluated independently.

Note: The meanings of some fields (runtime, defaultTimer) are not fully
confirmed from device experimentation.  Use caution when changing them until
their behaviour is better understood.
"""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .entity import PanasonicERVEntity

_CFM_MIN = 30           # hard floor for all CFM settings
_CFM_FALLBACK_MAX = 120 # used when the device hasn't reported its allowed range yet

# For each tier, the name of the tier directly above it in the speed hierarchy.
# None means boost — it has no tier above it; the device max is the only cap.
_TIER_ABOVE = {"low": "high", "high": "boost", "boost": None}

# Maps (direction, tier) → the device_config key holding that CFM target.
# Used to look up the tier-above value when computing the dynamic max.
_CFM_CONFIG_KEYS = {
    "supply":  {"low": "lowSa",  "high": "highSa",  "boost": "boostSa"},
    "exhaust": {"low": "lowEa",  "high": "highEa",  "boost": "boostEa"},
}

# CFM speed entities — dynamic max, enforced 10 CFM tier gap.
# (suffix, display_name, config_key, direction, tier, icon)
_CFM_NUMBER_DESCRIPTIONS = [
    ("cfg_low_sa",   "Low Speed Supply CFM",   "lowSa",   "supply",  "low",   "mdi:arrow-up-bold-circle-outline"),
    ("cfg_low_ea",   "Low Speed Exhaust CFM",  "lowEa",   "exhaust", "low",   "mdi:arrow-down-bold-circle-outline"),
    ("cfg_high_sa",  "High Speed Supply CFM",  "highSa",  "supply",  "high",  "mdi:arrow-up-bold-circle-outline"),
    ("cfg_high_ea",  "High Speed Exhaust CFM", "highEa",  "exhaust", "high",  "mdi:arrow-down-bold-circle-outline"),
    ("cfg_boost_sa", "Boost Supply CFM",       "boostSa", "supply",  "boost", "mdi:arrow-up-bold-circle-outline"),
    ("cfg_boost_ea", "Boost Exhaust CFM",      "boostEa", "exhaust", "boost", "mdi:arrow-down-bold-circle-outline"),
]

# Non-CFM numeric entities — fixed min/max, no dynamic constraints.
# (suffix, display_name, device_config_key, min, max, step, unit, icon, mode)
_NUMBER_DESCRIPTIONS = [
    (
        "cfg_runtime",
        "Runtime",
        "runtime",
        0, 480, 1,
        UnitOfTime.MINUTES,
        "mdi:timer-outline",
        NumberMode.BOX,
    ),
    (
        "cfg_default_timer",
        "Default Timer",
        "defaultTimer",
        0, 480, 1,
        UnitOfTime.MINUTES,
        "mdi:timer-settings-outline",
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
    """Create all number entities for this config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    entities = [
        PanasonicERVCFMNumber(coordinator, suffix, name, config_key, direction, tier, icon)
        for suffix, name, config_key, direction, tier, icon in _CFM_NUMBER_DESCRIPTIONS
    ]
    entities += [
        PanasonicERVNumber(
            coordinator, suffix, name, config_key,
            min_val, max_val, step, unit, icon, mode,
        )
        for suffix, name, config_key, min_val, max_val, step, unit, icon, mode
        in _NUMBER_DESCRIPTIONS
    ]
    async_add_entities(entities)


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


class PanasonicERVCFMNumber(PanasonicERVEntity, NumberEntity):
    """CFM setting entity with dynamic bounds derived from device capability and tier order.

    Maximum is recomputed each time HA reads the entity state:
      boost → device-reported max (from state[direction]["allowed"][1])
      high  → min(device_max, current boost value − 10)
      low   → min(device_max, current high value  − 10)

    Supply and exhaust are evaluated independently — supply low is capped against
    supply high, not exhaust high.

    If device_config hasn't loaded yet, or the tier-above value is missing,
    the entity falls back to the device-reported max with no tier cap applied.
    The result is always at least _CFM_MIN (30) so the range never inverts.
    """

    _attr_native_min_value = _CFM_MIN
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_entity_registry_enabled_default = False

    def __init__(
        self,
        coordinator,
        suffix: str,
        name: str,
        config_key: str,
        direction: str,
        tier: str,
        icon: str,
    ) -> None:
        super().__init__(coordinator, suffix)
        self._attr_name = name
        self._config_key = config_key
        self._direction = direction  # "supply" or "exhaust"
        self._tier = tier            # "low", "high", or "boost"
        self._attr_icon = icon
        self._attr_native_unit_of_measurement = "CFM"

    def _device_max(self) -> int:
        """Read the maximum CFM this installation supports from the live state.

        The device reports its physical airflow ceiling as an "allowed" array
        in the runtime state alongside the current CFM reading, e.g.:
          {"cfm": 61, "allowed": [0, 120]}
        This lets 100, 120, and 150 CFM units all use the same integration.
        """
        try:
            allowed = self.coordinator.data["host"]["components"]["0"][self._direction]["allowed"]
            return int(allowed[1])
        except (KeyError, TypeError, IndexError):
            return _CFM_FALLBACK_MAX

    @property
    def native_max_value(self) -> float:
        """Compute the effective ceiling for this speed tier.

        Overrides the base-class attribute so HA picks it up dynamically on
        every state read rather than using the static value set at init time.
        """
        device_max = self._device_max()
        tier_above = _TIER_ABOVE[self._tier]

        if tier_above is None:
            # Boost — only the physical device limit applies.
            return float(device_max)

        try:
            above_key = _CFM_CONFIG_KEYS[self._direction][tier_above]
            above_value = self.coordinator.device_config["host"]["components"]["0"][above_key]
            if above_value is not None:
                capped = int(above_value) - 10
                # Clamp between _CFM_MIN and device_max so we never produce an
                # inverted range if the tier-above value is unusually small.
                return float(max(_CFM_MIN, min(device_max, capped)))
        except (KeyError, TypeError):
            pass

        # device_config not yet loaded — fall back to device max without tier cap.
        return float(device_max)

    @property
    def native_value(self) -> float | None:
        """Read the current configured CFM from device_config."""
        try:
            return self.coordinator.device_config["host"]["components"]["0"][
                self._config_key
            ]
        except (KeyError, TypeError):
            return None

    @property
    def extra_state_attributes(self) -> dict:
        """Expose why the maximum is capped when a tier-gap constraint applies.

        Shown in the entity info panel and developer tools so users understand
        why the ceiling is lower than the device maximum.
        Example: "Must be ≥ 10 CFM below High Speed Supply CFM (currently 65 CFM)"
        """
        tier_above = _TIER_ABOVE[self._tier]
        if tier_above is None:
            return {}
        direction_label = "Supply" if self._direction == "supply" else "Exhaust"
        tier_label = tier_above.capitalize()
        try:
            above_key = _CFM_CONFIG_KEYS[self._direction][tier_above]
            above_value = int(
                self.coordinator.device_config["host"]["components"]["0"][above_key]
            )
            return {
                "max_limit": (
                    f"Must be ≥ 10 CFM below {tier_label} Speed {direction_label} CFM "
                    f"(currently {above_value} CFM) — max allowed: {int(self.native_max_value)} CFM"
                )
            }
        except (KeyError, TypeError):
            return {}

    async def async_set_value(self, value: float) -> None:
        """Validate the new value and raise a descriptive error for tier-gap violations.

        HA's default error just says "out of range X–Y".  When the ceiling comes
        from a tier-gap constraint (not the device physical limit), we surface a
        clearer message so the user knows which tier they need to adjust first.
        For all other out-of-range cases (below minimum, exceeds device max) we
        fall through to HA's standard validation via super().
        """
        tier_above = _TIER_ABOVE[self._tier]
        if tier_above is not None and value > self.native_max_value:
            direction_label = "Supply" if self._direction == "supply" else "Exhaust"
            tier_label = tier_above.capitalize()
            above_cfm = int(self.native_max_value) + 10
            raise ServiceValidationError(
                f"Must be at least 10 CFM below {tier_label} Speed {direction_label} CFM — "
                f"{tier_label} is currently {above_cfm} CFM, so the maximum here is "
                f"{int(self.native_max_value)} CFM."
            )
        await super().async_set_value(value)

    async def async_set_native_value(self, value: float) -> None:
        """Write the new CFM value to the device."""
        await self.coordinator.async_send_command(
            lambda: self.coordinator.api_client.async_set_device_config(
                self._config_key, int(value)
            )
        )
