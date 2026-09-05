import asyncio
from typing import Any

from modbus_connection import ModbusError

try:
    from four_noks_modbus import FourNoksGateway, FourNoksPlug
except ImportError:
    from .vendor.four_noks_modbus import FourNoksGateway, FourNoksPlug

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import EntityCategory
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
    elif isinstance(coordinator.device, FourNoksGateway):
        async_add_entities(
            [
                FourNoksGatewayDiscoverySwitch(coordinator),
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

    async def _async_wait_for_pending_clear(
        self, timeout: float = 5.0, poll_interval: float = 0.1
    ) -> None:
        """Wait until coil write pending status (DI 48) is cleared to False."""
        device = self.coordinator.device
        if hasattr(device, "switch") and hasattr(device.switch, "async_wait_pending"):
            await device.switch.async_wait_pending(
                timeout=timeout, poll_interval=poll_interval
            )
            return

        unit = getattr(device, "unit", None)
        if unit is None:
            return

        start_time = asyncio.get_running_loop().time()
        while asyncio.get_running_loop().time() - start_time < timeout:
            await asyncio.sleep(poll_interval)
            try:
                bits = await unit.read_discrete_inputs(48, 1)
                if bits and not bits[0]:
                    break
            except (ModbusError, OSError):
                pass

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        device = self.coordinator.device
        if isinstance(device, FourNoksPlug):
            await device.async_turn_on()
            await self._async_wait_for_pending_clear()
            await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        device = self.coordinator.device
        if isinstance(device, FourNoksPlug):
            await device.async_turn_off()
            await self._async_wait_for_pending_clear()
            await self.coordinator.async_refresh()


class FourNoksGatewayDiscoverySwitch(FourNoksEntity, SwitchEntity):
    """Switch entity controlling Zigbee network open / discovery on the Gateway."""

    _attr_translation_key = "discovery"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: FourNoksCoordinator) -> None:
        """Initialize the discovery switch."""
        super().__init__(coordinator, "discovery")

    @property
    def is_on(self) -> bool | None:
        """Return True if network open / discovery is active."""
        device = self.coordinator.device
        if isinstance(device, FourNoksGateway):
            return getattr(getattr(device, "network", None), "network_open_state", None)
        return None

    async def _async_wait_for_discovery_state(
        self, target_state: bool, timeout: float = 5.0, poll_interval: float = 0.2
    ) -> None:
        """Wait until network open state (DI 1) matches target_state."""
        unit = getattr(self.coordinator.device, "unit", None)
        if unit is None:
            return

        start_time = asyncio.get_running_loop().time()
        while asyncio.get_running_loop().time() - start_time < timeout:
            await asyncio.sleep(poll_interval)
            try:
                bits = await unit.read_discrete_inputs(1, 1)
                if bits and bits[0] == target_state:
                    break
            except (ModbusError, OSError):
                pass

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Open network for discovery (HR 0 = 5266, then Coil 0 = True)."""
        device = self.coordinator.device
        if isinstance(device, FourNoksGateway):
            await device.async_open_discovery()
            await self._async_wait_for_discovery_state(True)
            await self.coordinator.async_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Close network for discovery (HR 0 = 5267, then Coil 0 = True)."""
        device = self.coordinator.device
        if isinstance(device, FourNoksGateway):
            await device.async_close_discovery()
            await self._async_wait_for_discovery_state(False)
            await self.coordinator.async_refresh()



