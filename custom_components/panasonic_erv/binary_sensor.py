"""Panasonic ERV binary sensor entities."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_NAME, DATA_COORDINATOR, DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up binary sensor entities for Panasonic ERV."""
    coordinator = hass.data[DOMAIN][entry.entry_id][DATA_COORDINATOR]
    device_name = entry.data[CONF_DEVICE_NAME]

    async_add_entities(
        [
            PanasonicERVBinarySensor(
                coordinator,
                f"{device_name} Filter Needs Cleaning",
                ["host", "components", "0", "filter", "needsCleaning"],
            ),
            PanasonicERVBinarySensor(
                coordinator,
                f"{device_name} Filter Needs Replacement",
                ["host", "components", "0", "filter", "needsReplacement"],
            ),
        ],
        True,
    )


class PanasonicERVBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """Generic ERV binary sensor entity."""

    def __init__(self, coordinator, name: str, key_path: list[str]) -> None:
        super().__init__(coordinator)
        self._name = name
        self._key_path = key_path

    @property
    def unique_id(self) -> str:
        return f"{self._name}".lower().replace(" ", "_")

    @property
    def name(self) -> str:
        return self._name

    @property
    def is_on(self) -> bool:
        data = self.coordinator.data
        for key in self._key_path:
            if data is None or not isinstance(data, dict):
                return False
            data = data.get(key)
        return bool(data)
