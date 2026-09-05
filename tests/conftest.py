"""Fixtures for the 4-noks integration tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from homeassistant.const import CONF_HOST, CONF_PORT, CONF_TYPE
from homeassistant.core import HomeAssistant
from modbus_connection.mock import MockModbusConnection
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.four_noks.const import (
    CONF_CONNECTION,
    CONF_UNIT_ID,
    DOMAIN,
)

UNIT_ID_PLUG = 102
UNIT_ID_GATEWAY = 1
MODBUS_CONNECTION_DOMAIN = "modbus_connection"

PLUG_INPUT_REGISTERS: dict[int, int] = {
    0: 38,  # DeviceType.PLUG
    1: 2053,  # v20.53
    2: 150,  # messages_sent
    3: 135,  # signal_level_radio -> 35 dB
    4: 100,
    5: 2350,  # active_power -> 2350 W
    6: 5432,  # energy low word
    7: 1,  # energy high word -> 70968 Wh = 70.968 kWh
    8: 3600,  # measure_time
    9: 0,
    10: 15,
    11: 42,
    12: 1430,
    13: 140,
    14: 102,
}

PLUG_DISCRETE_INPUTS: dict[int, bool] = {
    0: True,  # switch output state
    1: False,  # standby killer status
    48: False,  # coil pending status (cleared)
    64: True,  # presence
    65: False,  # data valid
}

PLUG_HOLDING_REGISTERS: dict[int, int] = {
    1: 60,
    3: 300,
    4: 25,
}

GW_INPUT_REGISTERS: dict[int, int] = {
    0: 112,  # DeviceType.GATEWAY
    1: 748,  # v7.48
    2: 120,  # 20 dB
    3: 15,
    4: 12345,
    5: 43200,
    6: 9999,
    7: 5,
    8: 1,
    11: 150,
    12: 0,  # local end devices
    13: 2,  # bridge end devices
    14: 1,  # router neighbours
    15: 1,  # good router neighbours
    16: 64,
    21: 17,  # connected nodes
    22: 16,  # total routers
    23: 3,
}

GW_DISCRETE_INPUTS: dict[int, bool] = {
    0: True,  # network connected
    1: False,  # network open / discovery state
}
# Presence bits for nodes 16..127 (inputs 16..127)
for i in range(16, 128):
    GW_DISCRETE_INPUTS[i] = False
GW_DISCRETE_INPUTS[16] = True  # unconfigured node 16
GW_DISCRETE_INPUTS[17] = True  # unconfigured node 17
GW_DISCRETE_INPUTS[UNIT_ID_PLUG] = True  # configured node 102

# Data valid bits for nodes 16..127 (inputs 128..239)
for i in range(128, 240):
    GW_DISCRETE_INPUTS[i] = False
GW_DISCRETE_INPUTS[128 + (UNIT_ID_PLUG - 16)] = True  # node 102 data valid

GW_HOLDING_REGISTERS: dict[int, int] = {
    0: 0,
    3: 21,
    4: 1200,
    5: 20,
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations for testing."""
    yield


@pytest.fixture
def mock_modbus_connection() -> MockModbusConnection:
    """In-memory mock connection with seeded plug and gateway units."""
    conn = MockModbusConnection()

    # Seed plug unit
    plug = conn.for_unit(UNIT_ID_PLUG)
    plug.input.update(PLUG_INPUT_REGISTERS)
    plug.discrete_inputs.update(PLUG_DISCRETE_INPUTS)
    plug.holding.update(PLUG_HOLDING_REGISTERS)

    # Seed gateway unit
    gw = conn.for_unit(UNIT_ID_GATEWAY)
    gw.input.update(GW_INPUT_REGISTERS)
    gw.discrete_inputs.update(GW_DISCRETE_INPUTS)
    gw.holding.update(GW_HOLDING_REGISTERS)

    return conn


@pytest.fixture
def connection_entry(
    hass: HomeAssistant, mock_modbus_connection: MockModbusConnection
) -> MockConfigEntry:
    """A loaded modbus_connection entry backed by the in-memory mock."""
    from homeassistant.config_entries import ConfigEntryState

    entry = MockConfigEntry(
        domain=MODBUS_CONNECTION_DOMAIN,
        data={
            CONF_TYPE: "tcp",
            CONF_HOST: "192.168.2.3",
            CONF_PORT: 502,
        },
        title="Modbus Connection",
    )
    entry.add_to_hass(hass)
    entry.runtime_data = mock_modbus_connection
    entry.mock_state(hass, ConfigEntryState.LOADED)
    return entry


@pytest.fixture(autouse=True)
def mock_modbus_open(mock_modbus_connection: MockModbusConnection):
    """Prevent modbus_connection from opening real network sockets."""
    try:
        from custom_components.modbus_connection import _async_open  # noqa: F401

        modbus_conn_path = "custom_components.modbus_connection._async_open"
    except ImportError:
        modbus_conn_path = "homeassistant.components.modbus_connection._async_open"

    with (
        patch(
            modbus_conn_path,
            AsyncMock(return_value=mock_modbus_connection),
        ),
        patch(
            "custom_components.four_noks.async_get_unit",
            side_effect=lambda hass, conn_id, unit_id: mock_modbus_connection.for_unit(
                unit_id
            ),
        ),
        patch(
            "custom_components.four_noks.coordinator.async_get_unit",
            side_effect=lambda hass, conn_id, unit_id: mock_modbus_connection.for_unit(
                unit_id
            ),
        ),
        patch(
            "custom_components.four_noks.config_flow.async_get_unit",
            side_effect=lambda hass, conn_id, unit_id: mock_modbus_connection.for_unit(
                unit_id
            ),
        ),
    ):
        yield


@pytest.fixture
def mock_plug_config_entry(connection_entry: MockConfigEntry) -> MockConfigEntry:
    """A 4-noks Smart Plug config entry pointing to the connection entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_CONNECTION: connection_entry.entry_id,
            CONF_UNIT_ID: UNIT_ID_PLUG,
        },
        unique_id=f"{connection_entry.entry_id}_{UNIT_ID_PLUG}",
        title=f"ZR-PLUG-M ({UNIT_ID_PLUG})",
    )


@pytest.fixture
def mock_gateway_config_entry(connection_entry: MockConfigEntry) -> MockConfigEntry:
    """A 4-noks Gateway config entry pointing to the connection entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_CONNECTION: connection_entry.entry_id,
            CONF_UNIT_ID: UNIT_ID_GATEWAY,
        },
        unique_id=f"{connection_entry.entry_id}_{UNIT_ID_GATEWAY}",
        title=f"ZC-GW-ETH-EM ({UNIT_ID_GATEWAY})",
    )
