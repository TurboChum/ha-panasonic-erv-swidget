"""Binary sensor entities for the Panasonic ERV integration.

A binary sensor has two states: on (problem detected) or off (all clear).

This file provides two types of binary sensors:

1. Simple key-path sensors (PanasonicERVBinarySensor)
   Read a boolean value from a fixed path in the runtime state.  Used for
   filter cleaning and replacement alerts.

2. CFM mismatch sensors (PanasonicERVCFMMismatchSensor)
   Compare the measured airflow (CFM) from the runtime state against the
   configured target from device_config.  If the deviation exceeds the
   configured threshold for longer than the configured duration, the sensor
   turns on.  One sensor each for supply and exhaust airflow.

   The time-delay avoids false alarms during speed changes or brief upsets —
   the ERV needs time to ramp up or recover before we declare a problem.
"""

from datetime import timedelta

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    CFM_UNKNOWN_SENTINEL,
    CONF_CFM_ALERT_DURATION,
    CONF_CFM_ALERT_THRESHOLD,
    DATA_COORDINATOR,
    DEFAULT_CFM_ALERT_DURATION,
    DEFAULT_CFM_ALERT_THRESHOLD,
    DOMAIN,
)
from .entity import PanasonicERVEntity

# Maps direction ("supply" or "exhaust") and speed mode ("boost"/"high"/"low")
# to the device_config key that holds the target CFM for that combination.
_CFM_CONFIG_KEYS = {
    "supply": {
        "boost": "boostSa",
        "high":  "highSa",
        "low":   "lowSa",
    },
    "exhaust": {
        "boost": "boostEa",
        "high":  "highEa",
        "low":   "lowEa",
    },
}

# Simple binary sensors declared as (suffix, name, key_path, device_class).
_BINARY_SENSOR_DESCRIPTIONS = [
    (
        "filter_needs_cleaning",
        "Filter Needs Cleaning",
        ["host", "components", "0", "filter", "needsCleaning"],
        BinarySensorDeviceClass.PROBLEM,
    ),
    (
        "filter_needs_replacement",
        "Filter Needs Replacement",
        ["host", "components", "0", "filter", "needsReplacement"],
        BinarySensorDeviceClass.PROBLEM,
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create binary sensor entities for this config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        [
            *(
                PanasonicERVBinarySensor(coordinator, suffix, name, key_path, device_class)
                for suffix, name, key_path, device_class in _BINARY_SENSOR_DESCRIPTIONS
            ),
            PanasonicERVCFMMismatchSensor(coordinator, "supply"),
            PanasonicERVCFMMismatchSensor(coordinator, "exhaust"),
        ]
    )


class PanasonicERVBinarySensor(PanasonicERVEntity, BinarySensorEntity):
    """Generic binary sensor that reads a boolean from a fixed key path.

    Returns True (problem) if the value at key_path is truthy, False otherwise.
    Returns False (not None) on a missing key so the sensor stays "off" rather
    than "unavailable" when a field is absent.
    """

    def __init__(
        self,
        coordinator,
        suffix: str,
        name: str,
        key_path: list[str],
        device_class,
    ) -> None:
        super().__init__(coordinator, suffix)
        self._attr_name = name
        self._key_path = key_path
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data
        for key in self._key_path:
            if not isinstance(data, dict):
                return False
            data = data.get(key)
        return bool(data)


class PanasonicERVCFMMismatchSensor(PanasonicERVEntity, BinarySensorEntity):
    """Fires when measured CFM deviates from the configured target for too long.

    How it works:
      1. Determine the current speed mode (boost / high / low) from runtime state.
      2. Look up the target CFM for that mode from device_config.
      3. Compare against the actual CFM from runtime state.
      4. If the difference exceeds the threshold, start a timer (_mismatch_since).
      5. If the mismatch persists past the configured duration, return True (alert).
      6. If CFM returns to within range at any point, reset the timer.

    This time-delay approach prevents false alerts during normal spin-up,
    speed changes, or brief transient conditions where the ERV hasn't had time
    to stabilise yet.

    The sensor is unavailable until device_config has been fetched (so the
    target CFM is known) and will not alert when the device reports CFM = 255
    (the sentinel value for "not running / measurement unavailable").
    """

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:air-filter"

    def __init__(self, coordinator, direction: str) -> None:
        """Set up the sensor for one airflow direction.

        Args:
            direction: "supply" or "exhaust"
        """
        super().__init__(coordinator, f"cfm_mismatch_{direction}")
        self._direction = direction
        self._attr_name = f"{'Supply' if direction == 'supply' else 'Exhaust'} CFM Mismatch"
        self._mismatch_since = None  # timestamp of first detected deviation, or None

        # Read threshold and duration from options so users can tune them.
        options = coordinator.entry.options
        self._threshold: int = int(
            options.get(CONF_CFM_ALERT_THRESHOLD, DEFAULT_CFM_ALERT_THRESHOLD)
        )
        self._duration = timedelta(
            seconds=int(options.get(CONF_CFM_ALERT_DURATION, DEFAULT_CFM_ALERT_DURATION))
        )

    def _current_speed_key(self) -> str | None:
        """Return the speed mode string used to look up target CFM.

        Boost takes priority over speed because it overrides the normal CFM
        targets with its own (typically higher) values.
        """
        try:
            comp = self.coordinator.data["host"]["components"]["0"]
            if comp["boost"]["mode"] == "on":
                return "boost"
            return comp.get("speed")  # "low" or "high"
        except (KeyError, TypeError):
            return None

    def _target_cfm(self) -> int | None:
        """Look up the configured target CFM for the current speed mode."""
        speed_key = self._current_speed_key()
        if speed_key is None:
            return None
        try:
            cfg_key = _CFM_CONFIG_KEYS[self._direction][speed_key]
            return self.coordinator.device_config["host"]["components"]["0"][cfg_key]
        except (KeyError, TypeError):
            return None

    def _actual_cfm(self) -> int | None:
        """Read the current measured CFM from runtime state.

        Returns None for values that indicate the unit is not in a normal
        running state, suppressing mismatch alerts:
          - 255 (CFM_UNKNOWN_SENTINEL): unit off, recirc, exhaust-only, etc.
          - 0: defrost or other transient state where airflow is intentionally stopped.
        """
        try:
            value = self.coordinator.data["host"]["components"]["0"][self._direction]["cfm"]
        except (KeyError, TypeError):
            return None
        if value == CFM_UNKNOWN_SENTINEL or value == 0:
            return None
        return value

    @property
    def available(self) -> bool:
        """Only available once device_config has loaded and target CFM is known."""
        return (
            self.coordinator.last_update_success
            and bool(self.coordinator.device_config)
            and self._target_cfm() is not None
        )

    @property
    def is_on(self) -> bool | None:
        """Return True if CFM has been out of range for longer than _duration."""
        target = self._target_cfm()
        actual = self._actual_cfm()

        if target is None or actual is None:
            # Can't compare — reset the timer and report unknown.
            self._mismatch_since = None
            return None

        if abs(actual - target) > self._threshold:
            # Start the timer on first detection; keep it running on subsequent polls.
            if self._mismatch_since is None:
                self._mismatch_since = dt_util.utcnow()
            return (dt_util.utcnow() - self._mismatch_since) >= self._duration
        else:
            # CFM is back in range — clear the timer so the next deviation
            # starts a fresh countdown.
            self._mismatch_since = None
            return False

    @property
    def extra_state_attributes(self) -> dict:
        """Expose diagnostic values as entity attributes.

        These are visible in the Developer Tools → States panel and can be
        used in automations (e.g. notify when actual_cfm drops below target).
        """
        return {
            "target_cfm": self._target_cfm(),
            "actual_cfm": self._actual_cfm(),
            "speed_mode": self._current_speed_key(),
            "mismatch_since": (
                self._mismatch_since.isoformat() if self._mismatch_since else None
            ),
        }
