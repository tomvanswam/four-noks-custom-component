"""Fixtures for the 4-noks integration tests."""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from unittest.mock import patch

from homeassistant import loader
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from modbus_connection.mock import MockModbusConnection
import pytest

from custom_components.four_noks.const import (
    CONF_UNIT_ID,
    DOMAIN,
)
from tests.common import MockConfigEntry, async_test_home_assistant

UNIT_ID_PLUG = 102
UNIT_ID_GATEWAY = 1
TEST_HOST = "192.168.2.3"
TEST_PORT = 502

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
    0: True,  # output_state (relay ON)
    1: False,  # standby_killer_status
    2: True,  # network_state
    3: False,  # alarm_1
    4: False,  # alarm_2
    5: True,  # status_coil_1
    6: False,  # status_coil_2
    7: False,  # status_coil_3
    8: False,  # status_coil_4
    9: False,  # status_coil_5
    10: False,  # status_coil_6
    11: False,  # status_coil_7
    12: False,  # status_coil_8
    13: True,  # configured
    14: True,  # present
    48: False,  # coils_pending
    64: True,  # presence (Device Presence Status)
    65: False,  # general_pending
}

PLUG_HOLDING_REGISTERS: dict[int, int] = {
    0: 0,
    1: 0,
    2: 0,
    3: 0,
}

GW_INPUT_REGISTERS: dict[int, int] = {
    0: 112,  # DeviceType.GATEWAY
    1: 1000,  # firmware version
    2: 100,  # transmission power / RF
    3: 0,  # network channel
    4: 100,  # pan id
    5: 0,  # runtime
    6: 0,  # messages received
    7: 5,  # node_count (connected nodes)
    8: 0,  # gateway address
    9: 0,
    10: 0,
    11: 0,  # signal level
    12: 0,  # bridge_devices_count (bridge end devices)
    13: 2,  # end_devices_count (local end devices)
    14: 0,  # resets count
    15: 0,  # reset type
    16: 0,  # free packet buffer
    21: 17,  # routers_total
    22: 16,  # routers_neighbours
    23: 3,  # routers_good
}

GW_DISCRETE_INPUTS: dict[int, bool] = {
    0: True,  # connection_state (Gateway Connected to Zigbee Network)
    1: False,  # network_open_state
    2: True,  # network_state
    3: False,
    4: False,
    5: False,
    6: False,
    7: False,
    8: False,
    9: False,
    10: False,
    11: False,
    12: False,
    13: True,  # configured
    14: True,  # present
    # Active nodes table: presence (16..127), data validity (128..239)
    16: True,  # node 16 present (unconfigured)
    17: True,  # node 17 present (unconfigured)
    102: True,  # node 102 present (plug)
    128: True,  # node 16 valid
    129: True,  # node 17 valid
    214: True,  # node 102 valid
}

GW_HOLDING_REGISTERS: dict[int, int] = {
    0: 0,
}


@pytest.fixture
async def hass() -> AsyncGenerator[HomeAssistant, None]:
    """Return a test Home Assistant instance."""
    async with async_test_home_assistant() as hass_obj:
        yield hass_obj


@pytest.fixture
def enable_custom_integrations(hass: HomeAssistant) -> None:
    """Enable custom integrations defined in the test dir."""
    hass.data.pop(loader.DATA_CUSTOM_COMPONENTS, None)


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


@pytest.fixture(autouse=True)
def mock_modbus_open(mock_modbus_connection: MockModbusConnection):
    """Mock Home Assistant's native modbus connection getters."""

    @asynccontextmanager
    async def _mock_get_temporary_unit(hass, params, unit_id):
        yield mock_modbus_connection.for_unit(unit_id)

    def _mock_get_unit(hass, entry, params, unit_id):
        return mock_modbus_connection.for_unit(unit_id)

    with (
        patch(
            "custom_components.four_noks.async_get_unit",
            side_effect=_mock_get_unit,
        ),
        patch(
            "custom_components.four_noks.coordinator.async_get_unit",
            side_effect=_mock_get_unit,
        ),
        patch(
            "custom_components.four_noks.config_flow.async_get_temporary_unit",
            side_effect=_mock_get_temporary_unit,
        ),
        patch(
            "homeassistant.components.modbus.async_get_temporary_unit",
            side_effect=_mock_get_temporary_unit,
        ),
        patch(
            "homeassistant.components.modbus.async_get_unit",
            side_effect=_mock_get_unit,
        ),
    ):
        yield


@pytest.fixture
def mock_plug_config_entry() -> MockConfigEntry:
    """A 4-noks Smart Plug config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: TEST_HOST,
            CONF_PORT: TEST_PORT,
            CONF_UNIT_ID: UNIT_ID_PLUG,
        },
        unique_id=f"{TEST_HOST}:{TEST_PORT}:{UNIT_ID_PLUG}",
        title=f"ZR-PLUG-M ({UNIT_ID_PLUG})",
    )


@pytest.fixture
def mock_gateway_config_entry() -> MockConfigEntry:
    """A 4-noks Gateway config entry."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_HOST: TEST_HOST,
            CONF_PORT: TEST_PORT,
            CONF_UNIT_ID: UNIT_ID_GATEWAY,
        },
        unique_id=f"{TEST_HOST}:{TEST_PORT}:{UNIT_ID_GATEWAY}",
        title=f"ZC-GW-ETH-EM ({UNIT_ID_GATEWAY})",
    )
