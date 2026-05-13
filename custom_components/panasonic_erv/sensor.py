"""Panasonic ERV sensor entities."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.sensor import SensorEntity
from homeassistant.const import TEMP_CELSIUS, PERCENTAGE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_NAME, DATA_COORDINATOR, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensor entities for Panasonic ERV."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    device_name = entry.data[CONF_DEVICE_NAME]

    async_add_entities(
        [
            PanasonicERVSensor(
                coordinator,
                f"{device_name} Status",
                ["host", "components", "0", "status"],
            ),
            PanasonicERVSensor(
                coordinator,
                f"{device_name} Indoor Temperature",
                ["host", "components", "0", "indoors", "temperature"],
                TEMP_CELSIUS,
            ),
            PanasonicERVSensor(
                coordinator,
                f"{device_name} Indoor Humidity",
                ["host", "components", "0", "indoors", "humidity"],
                PERCENTAGE,
            ),
            PanasonicERVSensor(
                coordinator,
                f"{device_name} Outdoor Temperature",
                ["host", "components", "0", "outdoors", "temperature"],
                TEMP_CELSIUS,
            ),
            PanasonicERVSensor(
                coordinator,
                f"{device_name} Outdoor Humidity",
                ["host", "components", "0", "outdoors", "humidity"],
                PERCENTAGE,
            ),
            PanasonicERVSensor(
                coordinator,
                f"{device_name} Exhaust CFM",
                ["host", "components", "0", "exhaust", "cfm"],
                "cfm",
            ),
            PanasonicERVSensor(
                coordinator,
                f"{device_name} Supply CFM",
                ["host", "components", "0", "supply", "cfm"],
                "cfm",
            ),
            PanasonicERVSensor(
                coordinator,
                f"{device_name} Power Current",
                ["host", "components", "0", "power", "current"],
                "A",
            ),
            PanasonicERVSensor(
                coordinator,
                f"{device_name} Power Average",
                ["host", "components", "0", "power", "avg"],
                "A",
            ),
        ],
        True,
    )


class PanasonicERVSensor(CoordinatorEntity, SensorEntity):
    """Generic ERV sensor entity."""

    def __init__(self, coordinator, name: str, key_path: list[str], unit=None) -> None:
        super().__init__(coordinator)
        self._name = name
        self._key_path = key_path
        self._unit = unit

    @property
    def unique_id(self) -> str:
        return f"{self._name}".lower().replace(" ", "_")

    @property
    def name(self) -> str:
        return self._name

    @property
    def native_value(self):
        data = self.coordinator.data
        for key in self._key_path:
            if data is None or not isinstance(data, dict):
                return None
            data = data.get(key)
        return data

    @property
    def native_unit_of_measurement(self):
        return self._unit
