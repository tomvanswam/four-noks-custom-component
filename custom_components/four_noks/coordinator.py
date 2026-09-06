"""DataUpdateCoordinator for 4-noks Modbus devices."""

from datetime import timedelta
import logging

from homeassistant.components.modbus import async_get_unit
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from modbus_connection import ModbusError, ModbusTcpParams

try:
    from four_noks_modbus import FourNoksDevice
except ImportError:
    from .vendor.four_noks_modbus import FourNoksDevice

from .const import CONF_UNIT_ID, DEFAULT_SCAN_INTERVAL, DOMAIN

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
        scan_interval_sec = entry.options.get(
            CONF_SCAN_INTERVAL,
            entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
        )
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=scan_interval_sec),
        )
        self.device = device
        self.gateway_node_presence: bool | None = None
        self.gateway_node_data_valid: bool | None = None
        self.nodes_presence: dict[int, bool] = {}
        self.nodes_data_valid: dict[int, bool] = {}

    async def _async_update_data(self) -> FourNoksDevice:
        """Fetch data from the 4-noks device."""
        try:
            await self.device.async_update()
        except (ModbusError, OSError) as err:
            raise UpdateFailed(
                f"Error communicating with 4-noks device: {err}"
            ) from err

        unit_id = int(self.config_entry.data.get(CONF_UNIT_ID, 1))
        host = self.config_entry.data.get(CONF_HOST)
        port = int(self.config_entry.data.get(CONF_PORT, 502))

        # For gateway (unit 1), fetch full presence and data validity tables
        # (nodes 16..127)
        if unit_id == 1:
            try:
                unit = self.device.unit
                presence_bits = await unit.read_discrete_inputs(16, 112)
                validity_bits = await unit.read_discrete_inputs(128, 112)
                self.nodes_presence = {
                    16 + i: bool(presence_bits[i]) for i in range(len(presence_bits))
                }
                self.nodes_data_valid = {
                    16 + i: bool(validity_bits[i]) for i in range(len(validity_bits))
                }
            except (ModbusError, OSError) as err:
                _LOGGER.debug("Could not read gateway nodes status: %s", err)

        # For node devices (e.g. Smart Plug unit 16..126),
        # query gateway unit 1 for status
        if unit_id > 1 and host:
            try:
                params = ModbusTcpParams(host=host, port=port)
                gw_unit = async_get_unit(self.hass, self.config_entry, params, 1)
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
