"""Base entity for 4-noks integration."""

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_UNIT_ID, DOMAIN
from .coordinator import FourNoksCoordinator


class FourNoksEntity(CoordinatorEntity[FourNoksCoordinator]):
    """Common identity and DeviceInfo for 4-noks entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: FourNoksCoordinator, key: str) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        info = coordinator.device.info
        unit_id = entry.data[CONF_UNIT_ID]

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer=info.manufacturer,
            model=info.model,
            name=f"{info.model} ({unit_id})",
            sw_version=info.firmware_version,
        )
