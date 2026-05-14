"""Shared base class for all Panasonic ERV entities.

Every entity in this integration (switches, sensors, selects, etc.) extends
PanasonicERVEntity instead of CoordinatorEntity directly.  This base class
provides two things that every entity needs:

1. device_info — tells HA that all entities belong to the same physical device
   so they appear grouped together on one device card rather than scattered
   across the entity list.

2. unique_id — a stable identifier HA uses to remember an entity across
   restarts and renames.  It must never change for the lifetime of the
   config entry, which is why it is anchored to entry.entry_id (a UUID
   assigned by HA at setup) rather than to the user-visible device name.
"""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_NAME, CONF_FW_VERSION, CONF_MAC, CONF_MODEL_NAME, DOMAIN


class PanasonicERVEntity(CoordinatorEntity):
    """Base class for all Panasonic ERV entities.

    CoordinatorEntity wires the entity into the coordinator's update cycle:
    it subscribes to coordinator updates, marks the entity unavailable when
    the coordinator fails, and triggers a state write whenever new data arrives.
    This class adds device grouping and stable unique IDs on top of that.
    """

    # _attr_has_entity_name = True is an HA 2023+ convention that tells HA the
    # entity's name is relative to the device name.  With this set, if the
    # device is called "Upstairs ERV" and the entity name is "Power", HA will
    # display it as "Upstairs ERV Power" automatically.
    _attr_has_entity_name = True

    def __init__(self, coordinator, suffix: str) -> None:
        """Set up the entity.

        Args:
            coordinator: The shared data coordinator for this device.
            suffix: A short stable string (e.g. "power", "indoor_temperature")
                    appended to the entry_id to form the unique_id.
        """
        super().__init__(coordinator)
        # Using entry_id (a HA-assigned UUID) as the base ensures the unique_id
        # stays the same even if the user renames the device.  Using the device
        # name itself would break entity history and automations on rename.
        self._attr_unique_id = f"{coordinator.entry.entry_id}_{suffix}"

    @property
    def device_info(self) -> DeviceInfo:
        """Return device metadata that HA uses to group entities on one card.

        The MAC address (fetched from /api/v1/summary during setup) is used as
        the device identifier because it is tied to the physical hardware.
        If the MAC was not captured (e.g. older config entry), we fall back to
        the entry_id so the device card still appears.
        """
        entry = self.coordinator.entry
        return DeviceInfo(
            identifiers={(DOMAIN, entry.data.get(CONF_MAC, entry.entry_id))},
            name=entry.data.get(CONF_DEVICE_NAME, "Panasonic ERV"),
            manufacturer="Panasonic",
            model=entry.data.get(CONF_MODEL_NAME, "ERV"),
            sw_version=entry.data.get(CONF_FW_VERSION) or None,
        )
