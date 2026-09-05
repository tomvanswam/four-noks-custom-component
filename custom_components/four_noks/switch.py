"""Switch platform for 4-noks Smart Plugs."""

from typing import Any

try:
    from four_noks_modbus import FourNoksPlug
except ImportError:
    from .vendor.four_noks_modbus import FourNoksPlug

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import FourNoksConfigEntry, FourNoksCoordinator
from .entity import FourNoksEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: FourNoksConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the 4-noks switch platform."""
    coordinator = entry.runtime_data
    if isinstance(coordinator.device, FourNoksPlug):
        async_add_entities(
            [
                FourNoksPlugSwitch(coordinator),
            ]
        )


class FourNoksPlugSwitch(FourNoksEntity, SwitchEntity):
    """Switch entity controlling a 4-noks smart plug relay."""

    _attr_translation_key = "switch"

    def __init__(self, coordinator: FourNoksCoordinator) -> None:
        """Initialize the switch."""
        super().__init__(coordinator, "switch")

    @property
    def is_on(self) -> bool | None:
        """Return True if the switch is on."""
        device = self.coordinator.device
        if isinstance(device, FourNoksPlug):
            return device.switch.output_state
        return None

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        device = self.coordinator.device
        if isinstance(device, FourNoksPlug):
            await device.async_turn_on()
            await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        device = self.coordinator.device
        if isinstance(device, FourNoksPlug):
            await device.async_turn_off()
            await self.coordinator.async_request_refresh()
