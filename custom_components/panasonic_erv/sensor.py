"""Sensor entities for the Panasonic ERV integration.

All sensor values come from the coordinator's runtime state data
(coordinator.data), which is refreshed every poll cycle from /api/v1/state.

Rather than writing a separate class for each sensor, a single generic
PanasonicERVSensor class accepts a key_path (list of dict keys to traverse)
and reads the value from the nested state JSON.  All sensors are declared in
the _SENSOR_DESCRIPTIONS table at the top of this file, which keeps the setup
function short and makes it easy to add new sensors later.

SensorDeviceClass and SensorStateClass tell HA what kind of data the sensor
represents.  This enables automatic unit conversion, correct icons, and
inclusion in long-term statistics (energy dashboard, history graphs).
"""

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    PERCENTAGE,
    UnitOfPower,
    UnitOfTemperature,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CFM_UNKNOWN_SENTINEL, DATA_COORDINATOR, DOMAIN, TEMP_UNKNOWN_SENTINEL
from .entity import PanasonicERVEntity

# Each entry is a tuple of:
#   (suffix, display_name, key_path, unit, device_class, state_class, icon)
#
# key_path is the list of keys to traverse in coordinator.data to reach the
# value, e.g. ["host", "components", "0", "indoors", "temperature"].
#
# device_class=None means HA uses no special handling (plain text/number).
# icon=None means HA picks the icon automatically based on device_class.
_SENSOR_DESCRIPTIONS = [
    (
        "status",
        "Status",
        ["host", "components", "0", "status"],
        None,
        None,
        None,
        "mdi:information-outline",
    ),
    (
        "indoor_temperature",
        "Indoor Temperature",
        ["host", "components", "0", "indoors", "temperature"],
        UnitOfTemperature.CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        SensorStateClass.MEASUREMENT,
        None,  # HA provides a thermometer icon automatically for TEMPERATURE
    ),
    (
        "indoor_humidity",
        "Indoor Humidity",
        ["host", "components", "0", "indoors", "humidity"],
        PERCENTAGE,
        SensorDeviceClass.HUMIDITY,
        SensorStateClass.MEASUREMENT,
        None,
    ),
    (
        "outdoor_temperature",
        "Outdoor Temperature",
        ["host", "components", "0", "outdoors", "temperature"],
        UnitOfTemperature.CELSIUS,
        SensorDeviceClass.TEMPERATURE,
        SensorStateClass.MEASUREMENT,
        None,
    ),
    (
        "outdoor_humidity",
        "Outdoor Humidity",
        ["host", "components", "0", "outdoors", "humidity"],
        PERCENTAGE,
        SensorDeviceClass.HUMIDITY,
        SensorStateClass.MEASUREMENT,
        None,
    ),
    (
        "exhaust_cfm",
        "Exhaust CFM",
        ["host", "components", "0", "exhaust", "cfm"],
        "CFM",
        None,
        SensorStateClass.MEASUREMENT,
        "mdi:air-filter",
    ),
    (
        "supply_cfm",
        "Supply CFM",
        ["host", "components", "0", "supply", "cfm"],
        "CFM",
        None,
        SensorStateClass.MEASUREMENT,
        "mdi:air-filter",
    ),
    (
        "power_current",
        "Power",
        ["host", "components", "0", "power", "current"],
        UnitOfPower.WATT,
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
        None,
    ),
    (
        "power_avg",
        "Average Power",
        ["host", "components", "0", "power", "avg"],
        UnitOfPower.WATT,
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
        None,
    ),
    (
        "power_avg_on",
        "Average Power While On",
        ["host", "components", "0", "power", "avgOn"],
        UnitOfPower.WATT,
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
        None,
    ),
    # Duty Cycle — not useful for Panasonic ERV; left here for reference
    # (
    #     "duty_cycle",
    #     "Duty Cycle",
    #     ["host", "components", "0", "dutyCycle", "minutes"],
    #     UnitOfTime.MINUTES,
    #     None,
    #     SensorStateClass.MEASUREMENT,
    #     "mdi:timer-outline",
    # ),
    (
        "error",
        "Error",
        ["host", "components", "0", "error"],
        None,
        None,
        None,
        "mdi:alert-circle-outline",
    ),
]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Create one sensor entity per row in _SENSOR_DESCRIPTIONS."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        [
            PanasonicERVSensor(coordinator, suffix, name, key_path, unit, dc, sc, icon)
            for suffix, name, key_path, unit, dc, sc, icon in _SENSOR_DESCRIPTIONS
        ]
    )


class PanasonicERVSensor(PanasonicERVEntity, SensorEntity):
    """Generic read-only sensor that traverses a key path in coordinator.data.

    The key_path list is walked one key at a time.  If any key is missing or
    the data is not a dict at that point, the sensor returns None (shown as
    "unavailable" in HA) rather than raising an error.
    """

    def __init__(
        self,
        coordinator,
        suffix: str,
        name: str,
        key_path: list[str],
        unit,
        device_class,
        state_class,
        icon,
    ) -> None:
        super().__init__(coordinator, suffix)
        self._attr_name = name
        self._key_path = key_path
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        self._attr_state_class = state_class
        if icon:
            self._attr_icon = icon

    @property
    def native_value(self):
        """Walk the key_path and return the value, or None if not found.

        Special cases:
        - If the final value is a dict (e.g. the error field when there are
          active errors), convert it to a string so HA can display it.
        - If the unit is CFM and the value is 255, return None.  The device
          reports 255 as a sentinel meaning "not running / measurement
          unavailable", not an actual airflow reading.
        """
        data = self.coordinator.data
        for key in self._key_path:
            if not isinstance(data, dict):
                return None
            data = data.get(key)
        if isinstance(data, dict):
            return str(data) if data else None
        # CFM 255 means the unit is off/unavailable — return -1 to keep graphs continuous.
        if self._attr_native_unit_of_measurement == "CFM" and data == CFM_UNKNOWN_SENTINEL:
            return -1
        # Temperature 53°C (127.4°F) is a device sentinel for "no valid reading".
        # Return None so HA shows Unknown rather than a spurious spike.
        if self._attr_device_class == SensorDeviceClass.TEMPERATURE and data == TEMP_UNKNOWN_SENTINEL:
            return None
        return data
