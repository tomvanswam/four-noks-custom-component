"""Binary sensor platform for 4-noks devices."""

from collections.abc import Callable
from dataclasses import dataclass

try:
    from four_noks_modbus import FourNoksGateway, FourNoksPlug
except ImportError:
    from .vendor.four_noks_modbus import FourNoksGateway, FourNoksPlug

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import FourNoksConfigEntry, FourNoksCoordinator
from .entity import FourNoksEntity


@dataclass(frozen=True, kw_only=True)
class FourNoksBinarySensorDescription(BinarySensorEntityDescription):
    """Describes a 4-noks binary sensor entity."""

    is_on_fn: Callable[[FourNoksCoordinator], bool | None]


PLUG_BINARY_SENSORS: tuple[FourNoksBinarySensorDescription, ...] = (
    FourNoksBinarySensorDescription(
        key="presence",
        translation_key="presence",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda c: getattr(getattr(c.device, "switch", None), "presence", None),
    ),
    FourNoksBinarySensorDescription(
        key="standby_killer_status",
        translation_key="standby_killer_status",
        is_on_fn=lambda c: getattr(
            getattr(c.device, "switch", None), "standby_killer_status", None
        ),
    ),
    FourNoksBinarySensorDescription(
        key="general_pending",
        translation_key="general_pending",
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda c: getattr(
            getattr(c.device, "switch", None), "general_pending", None
        ),
    ),
    FourNoksBinarySensorDescription(
        key="gateway_presence",
        translation_key="gateway_presence",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda c: c.gateway_node_presence,
    ),
    FourNoksBinarySensorDescription(
        key="gateway_data_valid",
        translation_key="gateway_data_valid",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda c: c.gateway_node_data_valid,
    ),
)

GATEWAY_BINARY_SENSORS: tuple[FourNoksBinarySensorDescription, ...] = (
    FourNoksBinarySensorDescription(
        key="connection_state",
        translation_key="connection_state",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        is_on_fn=lambda c: getattr(
            getattr(c.device, "network", None), "connection_state", None
        ),
    ),
    FourNoksBinarySensorDescription(
        key="network_open_state",
        translation_key="network_open_state",
        device_class=BinarySensorDeviceClass.RUNNING,
        entity_category=EntityCategory.DIAGNOSTIC,
        is_on_fn=lambda c: getattr(
            getattr(c.device, "network", None), "network_open_state", None
        ),
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FourNoksConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up 4-noks binary sensors."""
    coordinator = entry.runtime_data
    descriptions: tuple[FourNoksBinarySensorDescription, ...] = ()

    if isinstance(coordinator.device, FourNoksPlug):
        descriptions = PLUG_BINARY_SENSORS
    elif isinstance(coordinator.device, FourNoksGateway):
        descriptions = GATEWAY_BINARY_SENSORS

    async_add_entities(FourNoksBinarySensor(coordinator, desc) for desc in descriptions)


class FourNoksBinarySensor(FourNoksEntity, BinarySensorEntity):
    """Representation of a 4-noks binary sensor entity."""

    entity_description: FourNoksBinarySensorDescription

    def __init__(
        self,
        coordinator: FourNoksCoordinator,
        description: FourNoksBinarySensorDescription,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator, description.key)
        self.entity_description = description

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        return self.entity_description.is_on_fn(self.coordinator)
