"""Panasonic ERV binary sensor entities."""

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


# Maps (boost, speed) to config keys for supply and exhaust target CFM
_CFM_CONFIG_KEYS = {
    "supply": {
        "boost": "boostSa",
        "high": "highSa",
        "low": "lowSa",
    },
    "exhaust": {
        "boost": "boostEa",
        "high": "highEa",
        "low": "lowEa",
    },
}

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
    """Generic ERV binary sensor entity."""

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
    """Binary sensor that fires when actual CFM deviates from the configured target for over a minute.

    Compares the measured CFM from the state endpoint against the target CFM from
    device_config for the current speed (low/high/boost). Returns True only after
    the mismatch has persisted for CFM_ALERT_DURATION to avoid false alerts on
    transient spin-up/down conditions.
    """

    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_icon = "mdi:air-filter"

    def __init__(self, coordinator, direction: str) -> None:
        super().__init__(coordinator, f"cfm_mismatch_{direction}")
        self._direction = direction  # "supply" or "exhaust"
        self._attr_name = f"{'Supply' if direction == 'supply' else 'Exhaust'} CFM Mismatch"
        self._mismatch_since = None
        options = coordinator.entry.options
        self._threshold: int = int(
            options.get(CONF_CFM_ALERT_THRESHOLD, DEFAULT_CFM_ALERT_THRESHOLD)
        )
        self._duration = timedelta(
            seconds=int(options.get(CONF_CFM_ALERT_DURATION, DEFAULT_CFM_ALERT_DURATION))
        )

    def _current_speed_key(self) -> str | None:
        """Return 'boost', 'high', or 'low' based on live device state."""
        try:
            comp = self.coordinator.data["host"]["components"]["0"]
            if comp["boost"]["mode"] == "on":
                return "boost"
            return comp.get("speed")  # "low" or "high"
        except (KeyError, TypeError):
            return None

    def _target_cfm(self) -> int | None:
        speed_key = self._current_speed_key()
        if speed_key is None:
            return None
        try:
            cfg_key = _CFM_CONFIG_KEYS[self._direction][speed_key]
            return self.coordinator.device_config["host"]["components"]["0"][cfg_key]
        except (KeyError, TypeError):
            return None

    def _actual_cfm(self) -> int | None:
        try:
            value = self.coordinator.data["host"]["components"]["0"][self._direction]["cfm"]
        except (KeyError, TypeError):
            return None
        # Device reports 255 when measurement is unavailable or unit is not running
        if value == CFM_UNKNOWN_SENTINEL:
            return None
        return value

    @property
    def available(self) -> bool:
        return (
            self.coordinator.last_update_success
            and bool(self.coordinator.device_config)
            and self._target_cfm() is not None
        )

    @property
    def is_on(self) -> bool | None:
        target = self._target_cfm()
        actual = self._actual_cfm()

        if target is None or actual is None:
            self._mismatch_since = None
            return None

        if abs(actual - target) > self._threshold:
            if self._mismatch_since is None:
                self._mismatch_since = dt_util.utcnow()
            return (dt_util.utcnow() - self._mismatch_since) >= self._duration
        else:
            self._mismatch_since = None
            return False

    @property
    def extra_state_attributes(self) -> dict:
        return {
            "target_cfm": self._target_cfm(),
            "actual_cfm": self._actual_cfm(),
            "speed_mode": self._current_speed_key(),
            "mismatch_since": (
                self._mismatch_since.isoformat() if self._mismatch_since else None
            ),
        }
