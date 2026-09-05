"""The 4-noks integration.

4-noks devices communicate over Modbus. This integration borrows a ``ModbusUnit``
from a ``modbus_connection`` config entry and delegates device handling to the
``four_noks_modbus`` library.
"""

try:
    from four_noks_modbus import async_probe_device
except ImportError:
    from .vendor.four_noks_modbus import async_probe_device

try:
    from homeassistant.components.modbus_connection import async_get_unit
except ImportError:
    from custom_components.modbus_connection import async_get_unit
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_CONNECTION, CONF_UNIT_ID
from .coordinator import FourNoksConfigEntry, FourNoksCoordinator

PLATFORMS = [
    Platform.BINARY_SENSOR,
    Platform.BUTTON,
    Platform.NUMBER,
    Platform.SENSOR,
    Platform.SWITCH,
]


async def async_setup_entry(hass: HomeAssistant, entry: FourNoksConfigEntry) -> bool:
    """Set up 4-noks from a config entry."""
    unit = async_get_unit(
        hass, entry.data[CONF_CONNECTION], int(entry.data[CONF_UNIT_ID])
    )
    device = await async_probe_device(unit)
    coordinator = FourNoksCoordinator(hass, entry, device)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    # Reload on connection drop so unit is re-borrowed on fresh transport
    entry.async_on_unload(
        unit.on_connection_lost(
            lambda: hass.config_entries.async_schedule_reload(entry.entry_id)
        )
    )

    # Reload on options update (e.g. scan interval changed)
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: FourNoksConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def async_reload_entry(hass: HomeAssistant, entry: FourNoksConfigEntry) -> None:
    """Reload config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)

