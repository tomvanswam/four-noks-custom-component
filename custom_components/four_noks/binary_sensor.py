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

from .const import CONF_CONNECTION, CONF_UNIT_ID, DOMAIN
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

    if isinstance(coordinator.device, FourNoksPlug):
        async_add_entities(
            FourNoksBinarySensor(coordinator, desc) for desc in PLUG_BINARY_SENSORS
        )
    elif isinstance(coordinator.device, FourNoksGateway):
        entities: list[BinarySensorEntity] = [
            FourNoksBinarySensor(coordinator, desc) for desc in GATEWAY_BINARY_SENSORS
        ]

        # Add presence and data_valid for each child device configured on this connection
        conn_id = entry.data.get(CONF_CONNECTION)
        for conf_entry in hass.config_entries.async_entries(DOMAIN):
            if (
                conf_entry.data.get(CONF_CONNECTION) == conn_id
                and int(conf_entry.data.get(CONF_UNIT_ID, 1)) > 1
            ):
                child_unit = int(conf_entry.data[CONF_UNIT_ID])
                entities.append(
                    FourNoksGatewayNodeBinarySensor(coordinator, child_unit, "presence")
                )
                entities.append(
                    FourNoksGatewayNodeBinarySensor(coordinator, child_unit, "data_valid")
                )

        async_add_entities(entities)


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


class FourNoksGatewayNodeBinarySensor(FourNoksEntity, BinarySensorEntity):
    """Binary sensor on the Gateway device representing a child device's presence or data validity."""

    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(
        self,
        coordinator: FourNoksCoordinator,
        node_unit_id: int,
        sensor_type: str,
    ) -> None:
        """Initialize the gateway node binary sensor."""
        key = f"node_{node_unit_id}_{sensor_type}"
        super().__init__(coordinator, key)
        self._node_unit_id = node_unit_id
        self._sensor_type = sensor_type
        self._attr_translation_key = f"device_node_{sensor_type}"
        self._attr_translation_placeholders = {"node_id": str(node_unit_id)}

    @property
    def is_on(self) -> bool | None:
        """Return true if node is present or data is valid."""
        if self._sensor_type == "presence":
            return self.coordinator.nodes_presence.get(self._node_unit_id)
        return self.coordinator.nodes_data_valid.get(self._node_unit_id)

