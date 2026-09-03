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

try:
    from homeassistant.components.modbus_connection import async_get_unit
except ImportError:
    from custom_components.modbus_connection import async_get_unit

from .const import CONF_CONNECTION, CONF_UNIT_ID, DOMAIN, SCAN_INTERVAL

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
        self.gateway_node_presence: bool | None = None
        self.gateway_node_data_valid: bool | None = None

    async def _async_update_data(self) -> FourNoksDevice:
        """Fetch data from device and gateway status."""
        try:
            await self.device.async_update()
        except ModbusError as err:
            raise UpdateFailed(
                f"Error communicating with 4-noks device: {err}"
            ) from err

        unit_id = int(self.config_entry.data.get(CONF_UNIT_ID, 1))
        connection_id = self.config_entry.data.get(CONF_CONNECTION)

        # For node devices (e.g. Smart Plug unit 16..126),
        # query gateway unit 1 for status
        if unit_id > 1 and connection_id:
            try:
                gw_unit = async_get_unit(self.hass, connection_id, 1)
                # Discrete input at unit_id (presence)
                presence_bits = await gw_unit.read_discrete_inputs(unit_id, 1)
                self.gateway_node_presence = (
                    bool(presence_bits[0]) if presence_bits else None
                )

                # Discrete input at 128 + unit_id - 16 (data validity)
                validity_addr = 128 + unit_id - 16
                valid_bits = await gw_unit.read_discrete_inputs(validity_addr, 1)
                self.gateway_node_data_valid = (
                    bool(valid_bits[0]) if valid_bits else None
                )
            except (ModbusError, OSError) as err:
                _LOGGER.debug(
                    "Could not read gateway status for unit %s: %s", unit_id, err
                )

        return self.device
