"""Sensor platform for 4-noks devices."""

from collections.abc import Callable
from dataclasses import dataclass

try:
    from four_noks_modbus import FourNoksDevice, FourNoksGateway, FourNoksPlug
except ImportError:
    from .vendor.four_noks_modbus import FourNoksDevice, FourNoksGateway, FourNoksPlug

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import (
    SIGNAL_STRENGTH_DECIBELS,
    UnitOfEnergy,
    UnitOfPower,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import FourNoksConfigEntry, FourNoksCoordinator
from .entity import FourNoksEntity


@dataclass(frozen=True, kw_only=True)
class FourNoksSensorDescription(SensorEntityDescription):
    """Describes a 4-noks sensor entity."""

    value_fn: Callable[[FourNoksDevice], float | int | str | None]


PLUG_SENSORS: tuple[FourNoksSensorDescription, ...] = (
    FourNoksSensorDescription(
        key="active_power",
        translation_key="active_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda d: getattr(
            getattr(d, "measurements", None), "active_power", None
        ),
    ),
    FourNoksSensorDescription(
        key="energy_consumed",
        translation_key="energy_consumed",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=lambda d: getattr(
            getattr(d, "measurements", None), "energy_consumed_kwh", None
        ),
    ),
    FourNoksSensorDescription(
        key="signal_level_radio",
        translation_key="signal_level_radio",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: getattr(
            getattr(d, "measurements", None), "signal_level_radio", None
        ),
    ),
    FourNoksSensorDescription(
        key="measure_time",
        translation_key="measure_time",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: getattr(
            getattr(d, "measurements", None), "measure_time", None
        ),
    ),
    FourNoksSensorDescription(
        key="messages_sent",
        translation_key="messages_sent",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: getattr(
            getattr(d, "measurements", None), "messages_sent", None
        ),
    ),
)

GATEWAY_SENSORS: tuple[FourNoksSensorDescription, ...] = (
    FourNoksSensorDescription(
        key="transmission_power",
        translation_key="transmission_power",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: getattr(
            getattr(d, "radio", None), "transmission_power", None
        ),
    ),
    FourNoksSensorDescription(
        key="signal_level",
        translation_key="signal_level",
        device_class=SensorDeviceClass.SIGNAL_STRENGTH,
        native_unit_of_measurement=SIGNAL_STRENGTH_DECIBELS,
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: getattr(getattr(d, "radio", None), "signal_level", None),
    ),
    FourNoksSensorDescription(
        key="runtime",
        translation_key="runtime",
        device_class=SensorDeviceClass.DURATION,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: getattr(getattr(d, "radio", None), "runtime", None),
    ),
    FourNoksSensorDescription(
        key="messages_received",
        translation_key="messages_received",
        state_class=SensorStateClass.TOTAL_INCREASING,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: getattr(
            getattr(d, "radio", None), "messages_received", None
        ),
    ),
    FourNoksSensorDescription(
        key="node_count",
        translation_key="node_count",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: getattr(getattr(d, "radio", None), "node_count", None),
    ),
    FourNoksSensorDescription(
        key="routers_total",
        translation_key="routers_total",
        state_class=SensorStateClass.MEASUREMENT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: getattr(getattr(d, "radio", None), "routers_total", None),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FourNoksConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up 4-noks sensors."""
    coordinator = entry.runtime_data
    descriptions: tuple[FourNoksSensorDescription, ...] = ()

    if isinstance(coordinator.device, FourNoksPlug):
        descriptions = PLUG_SENSORS
    elif isinstance(coordinator.device, FourNoksGateway):
        descriptions = GATEWAY_SENSORS

    async_add_entities(FourNoksSensor(coordinator, desc) for desc in descriptions)


class FourNoksSensor(FourNoksEntity, SensorEntity):
    """Representation of a 4-noks sensor entity."""

    entity_description: FourNoksSensorDescription

    def __init__(
        self,
        coordinator: FourNoksCoordinator,
        description: FourNoksSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def native_value(self) -> float | int | str | None:
        """Return native state value."""
        return self.entity_description.value_fn(self.coordinator.device)
