"""Panasonic ERV binary sensor entities."""

from homeassistant.components.binary_sensor import BinarySensorEntity

class PanasonicERVBinarySensor(BinarySensorEntity):
    """Generic ERV binary sensor entity."""

    def __init__(self, coordinator, name, key_path):
        self.coordinator = coordinator
        self._name = name
        self._key_path = key_path

    @property
    def name(self):
        return f"{self._name}"

    @property
    def is_on(self):
        data = self.coordinator.data
        for key in self._key_path:
            data = data[key]
        return bool(data)
