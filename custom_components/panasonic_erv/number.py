"""Panasonic ERV number entities for device configuration."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DATA_COORDINATOR, DOMAIN
from .entity import PanasonicERVEntity

# (suffix, name, config_key, min_val, max_val, step, unit, icon, mode)
_NUMBER_DESCRIPTIONS = [
    (
        "cfg_low_sa",
        "Low Speed Supply CFM",
        "lowSa",
        0, 120, 1,
        "CFM",
        "mdi:arrow-up-bold-circle-outline",
        NumberMode.BOX,
    ),
    (
        "cfg_low_ea",
        "Low Speed Exhaust CFM",
        "lowEa",
        0, 120, 1,
        "CFM",
        "mdi:arrow-down-bold-circle-outline",
        NumberMode.BOX,
    ),
    (
        "cfg_high_sa",
        "High Speed Supply CFM",
        "highSa",
        0, 120, 1,
        "CFM",
        "mdi:arrow-up-bold-circle-outline",
        NumberMode.BOX,
    ),
    (
        "cfg_high_ea",
        "High Speed Exhaust CFM",
        "highEa",
        0, 120, 1,
        "CFM",
        "mdi:arrow-down-bold-circle-outline",
        NumberMode.BOX,
    ),
    (
        "cfg_boost_sa",
        "Boost Supply CFM",
        "boostSa",
        0, 120, 1,
        "CFM",
        "mdi:arrow-up-bold-circle-outline",
        NumberMode.BOX,
    ),
    (
        "cfg_boost_ea",
        "Boost Exhaust CFM",
        "boostEa",
        0, 120, 1,
        "CFM",
        "mdi:arrow-down-bold-circle-outline",
        NumberMode.BOX,
    ),
    (
        "cfg_runtime",
        "Runtime",
        "runtime",
        0, 480, 1,
        UnitOfTime.MINUTES,
        "mdi:timer-outline",
        NumberMode.BOX,
    ),
    (
        "cfg_humidity_control_setting",
        "Humidity Control Setpoint",
        "humidityControlSetting",
        0, 100, 1,
        PERCENTAGE,
        "mdi:water-percent",
        NumberMode.SLIDER,
    ),
    (
        "cfg_high_humidity_threshold",
        "High Humidity Threshold",
        "highHumidityThreshold",
        0, 100, 1,
        PERCENTAGE,
        "mdi:water-percent",
        NumberMode.SLIDER,
    ),
    (
        "cfg_low_temp_threshold",
        "Low Temperature Threshold",
        "lowTempThreshold",
        -30, 30, 1,
        UnitOfTemperature.CELSIUS,
        "mdi:thermometer-low",
        NumberMode.BOX,
    ),
    (
        "cfg_supply_limit_low_temp",
        "Supply Limit Low Temp",
        "supplyLimitLowTemp",
        0, 1, 1,
        None,
        "mdi:thermometer-minus",
        NumberMode.BOX,
    ),
    (
        "cfg_supply_limit_high_hum",
        "Supply Limit High Humidity",
        "supplyLimitHighHum",
        0, 1, 1,
        None,
        "mdi:water-percent",
        NumberMode.BOX,
    ),
    (
        "cfg_log_rate",
        "Log Rate",
        "log_rate",
        60000, 3600000, 1000,
        UnitOfTime.MILLISECONDS,
        "mdi:clipboard-clock-outline",
        NumberMode.BOX,
    ),
    (
        "cfg_offset",
        "Balancing Offset",
        "offset",
        -10, 10, 1,
        "CFM",
        "mdi:scale-balance",
        NumberMode.BOX,
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
            PanasonicERVNumber(
                coordinator, suffix, name, config_key,
                min_val, max_val, step, unit, icon, mode,
            )
            for suffix, name, config_key, min_val, max_val, step, unit, icon, mode
            in _NUMBER_DESCRIPTIONS
        ]
    )


class PanasonicERVNumber(PanasonicERVEntity, NumberEntity):
    """A number entity backed by a device_config field."""

    def __init__(
        self,
        coordinator,
        suffix: str,
        name: str,
        config_key: str,
        min_val: float,
        max_val: float,
        step: float,
        unit,
        icon: str,
        mode: NumberMode,
    ) -> None:
        super().__init__(coordinator, suffix)
        self._attr_name = name
        self._config_key = config_key
        self._attr_native_min_value = min_val
        self._attr_native_max_value = max_val
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit
        self._attr_icon = icon
        self._attr_mode = mode
        self._attr_entity_registry_enabled_default = False

    @property
    def native_value(self) -> float | None:
        try:
            return self.coordinator.device_config["host"]["components"]["0"][
                self._config_key
            ]
        except (KeyError, TypeError):
            return None

    async def async_set_native_value(self, value: float) -> None:
        int_value = int(value) if self._attr_native_step == 1 else value
        await self.coordinator.async_send_command(
            lambda: self.coordinator.api_client.async_set_device_config(
                self._config_key, int_value
            )
        )
