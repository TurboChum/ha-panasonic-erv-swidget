"""Panasonic ERV sensor entities."""

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
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CFM_UNKNOWN_SENTINEL, DATA_COORDINATOR, DOMAIN
from .entity import PanasonicERVEntity

# (suffix, name, key_path, unit, device_class, state_class, icon)
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
        None,
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
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    async_add_entities(
        [
            PanasonicERVSensor(coordinator, suffix, name, key_path, unit, dc, sc, icon)
            for suffix, name, key_path, unit, dc, sc, icon in _SENSOR_DESCRIPTIONS
        ]
    )


class PanasonicERVSensor(PanasonicERVEntity, SensorEntity):
    """Generic ERV sensor entity."""

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
        data = self.coordinator.data
        for key in self._key_path:
            if not isinstance(data, dict):
                return None
            data = data.get(key)
        if isinstance(data, dict):
            return str(data) if data else None
        # Device reports 255 as a sentinel for "unknown / not running" on CFM fields
        if self._attr_native_unit_of_measurement == "CFM" and data == CFM_UNKNOWN_SENTINEL:
            return None
        return data
