"""Base entity for Panasonic ERV."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_NAME, CONF_FW_VERSION, CONF_MAC, CONF_MODEL_NAME, DOMAIN


class PanasonicERVEntity(CoordinatorEntity):
    """Base class for all Panasonic ERV entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, suffix: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{suffix}"

    @property
    def device_info(self) -> DeviceInfo:
        entry = self.coordinator.entry
        return DeviceInfo(
            identifiers={(DOMAIN, entry.data.get(CONF_MAC, entry.entry_id))},
            name=entry.data.get(CONF_DEVICE_NAME, "Panasonic ERV"),
            manufacturer="Panasonic",
            model=entry.data.get(CONF_MODEL_NAME, "ERV"),
            sw_version=entry.data.get(CONF_FW_VERSION) or None,
        )
