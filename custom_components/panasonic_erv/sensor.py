"""Panasonic ERV sensor entities."""

from homeassistant.components.sensor import SensorEntity

class PanasonicERVSensor(SensorEntity):
    """Generic ERV sensor entity."""

    def __init__(self, coordinator, name, key_path, unit=None):
        self.coordinator = coordinator
        self._name = name
        self._key_path = key_path
        self._unit = unit

    @property
    def name(self):
        return f"{self._name}"

    @property
    def native_value(self):
        data = self.coordinator.data
        for key in self._key_path:
            data = data[key]
        return data

    @property
    def native_unit_of_measurement(self):
        return self._unit
