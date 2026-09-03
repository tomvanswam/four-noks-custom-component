"""DataUpdateCoordinator for 4-noks Modbus devices."""

import logging

try:
    from four_noks_modbus import FourNoksDevice
except ImportError:
    from .vendor.four_noks_modbus import FourNoksDevice

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import ModbusError

from .const import DOMAIN, SCAN_INTERVAL

_LOGGER = logging.getLogger(__name__)

type FourNoksConfigEntry = ConfigEntry[FourNoksCoordinator]


class FourNoksCoordinator(DataUpdateCoordinator[FourNoksDevice]):
    """Refreshes 4-noks device data on a regular schedule."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: FourNoksConfigEntry,
        device: FourNoksDevice,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=SCAN_INTERVAL,
        )
        self.device = device

    async def _async_update_data(self) -> FourNoksDevice:
        try:
            await self.device.async_update()
        except ModbusError as err:
            raise UpdateFailed(
                f"Error communicating with 4-noks device: {err}"
            ) from err
        return self.device
