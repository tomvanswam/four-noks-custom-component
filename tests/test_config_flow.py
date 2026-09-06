"""Tests for the 4-noks config flow."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_HOST, CONF_PORT, CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from modbus_connection import ModbusError
from modbus_connection.mock import MockModbusConnection
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.four_noks.config_flow import (
    CONF_AUTO_DISCOVER,
    CONF_SELECTED_NODES,
)
from custom_components.four_noks.const import (
    CONF_UNIT_ID,
    DOMAIN,
)

from .conftest import TEST_HOST, TEST_PORT, UNIT_ID_GATEWAY, UNIT_ID_PLUG


async def test_user_flow_smart_plug(hass: HomeAssistant) -> None:
    """Selecting host, port and plug unit probes the plug and creates the entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: TEST_HOST,
            CONF_PORT: TEST_PORT,
            CONF_UNIT_ID: UNIT_ID_PLUG,
            CONF_AUTO_DISCOVER: False,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"ZR-PLUG-M ({UNIT_ID_PLUG})"
    assert result["data"][CONF_HOST] == TEST_HOST
    assert result["data"][CONF_PORT] == TEST_PORT
    assert result["data"][CONF_UNIT_ID] == UNIT_ID_PLUG


async def test_user_flow_gateway(hass: HomeAssistant) -> None:
    """Selecting host, port and gateway unit probes and creates the entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: TEST_HOST,
            CONF_PORT: TEST_PORT,
            CONF_UNIT_ID: UNIT_ID_GATEWAY,
            CONF_AUTO_DISCOVER: False,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"ZC-GW-ETH-EM ({UNIT_ID_GATEWAY})"
    assert result["data"][CONF_HOST] == TEST_HOST
    assert result["data"][CONF_PORT] == TEST_PORT
    assert result["data"][CONF_UNIT_ID] == UNIT_ID_GATEWAY


async def test_user_flow_gateway_discovery_step(hass: HomeAssistant) -> None:
    """Gateway flow with auto_discover shows discovery step and creates entries."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_HOST: TEST_HOST,
            CONF_PORT: TEST_PORT,
            CONF_UNIT_ID: UNIT_ID_GATEWAY,
            CONF_AUTO_DISCOVER: True,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discover_nodes"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_SELECTED_NODES: [str(UNIT_ID_GATEWAY), str(UNIT_ID_PLUG)]},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"ZC-GW-ETH-EM ({UNIT_ID_GATEWAY})"
    assert result["data"][CONF_UNIT_ID] == UNIT_ID_GATEWAY


async def test_user_flow_cannot_connect(
    hass: HomeAssistant,
    mock_modbus_connection: MockModbusConnection,
) -> None:
    """A connection failure during probe surfaces cannot_connect error."""
    plug_unit = mock_modbus_connection.for_unit(UNIT_ID_PLUG)

    with patch.object(
        plug_unit, "read_input_registers", side_effect=ModbusError("Connection lost")
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {
                CONF_HOST: TEST_HOST,
                CONF_PORT: TEST_PORT,
                CONF_UNIT_ID: UNIT_ID_PLUG,
                CONF_AUTO_DISCOVER: False,
            },
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


async def test_options_flow_smart_plug(
    hass: HomeAssistant,
    mock_plug_config_entry: MockConfigEntry,
) -> None:
    """Test options flow for smart plug only configures scan interval."""
    mock_plug_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_plug_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(
        mock_plug_config_entry.entry_id
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert CONF_HOST not in result["data_schema"].schema

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SCAN_INTERVAL: 15},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_plug_config_entry.options[CONF_SCAN_INTERVAL] == 15


async def test_options_flow_gateway_scan_interval(
    hass: HomeAssistant,
    mock_gateway_config_entry: MockConfigEntry,
) -> None:
    """Test updating scan interval on gateway preserves connection settings."""
    mock_gateway_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_gateway_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(
        mock_gateway_config_entry.entry_id
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"
    assert CONF_HOST in result["data_schema"].schema

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: TEST_HOST,
            CONF_PORT: TEST_PORT,
            CONF_UNIT_ID: UNIT_ID_GATEWAY,
            CONF_SCAN_INTERVAL: 60,
            CONF_AUTO_DISCOVER: False,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_gateway_config_entry.options[CONF_SCAN_INTERVAL] == 60
    assert mock_gateway_config_entry.data[CONF_HOST] == TEST_HOST
    assert mock_gateway_config_entry.data[CONF_PORT] == TEST_PORT


async def test_options_flow_gateway_update_connection_and_propagate(
    hass: HomeAssistant,
    mock_gateway_config_entry: MockConfigEntry,
    mock_plug_config_entry: MockConfigEntry,
) -> None:
    """Test updating gateway host/port propagates to child plug entries."""
    mock_gateway_config_entry.add_to_hass(hass)
    mock_plug_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_gateway_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(
        mock_gateway_config_entry.entry_id
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    new_host = "192.168.2.99"
    new_port = 5020
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: new_host,
            CONF_PORT: new_port,
            CONF_UNIT_ID: UNIT_ID_GATEWAY,
            CONF_SCAN_INTERVAL: 45,
            CONF_AUTO_DISCOVER: False,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_gateway_config_entry.options[CONF_SCAN_INTERVAL] == 45
    assert mock_gateway_config_entry.data[CONF_HOST] == new_host
    assert mock_gateway_config_entry.data[CONF_PORT] == new_port
    assert (
        mock_gateway_config_entry.unique_id
        == f"{new_host}:{new_port}:{UNIT_ID_GATEWAY}"
    )

    # Verify child plug's host and port are also updated
    assert mock_plug_config_entry.data[CONF_HOST] == new_host
    assert mock_plug_config_entry.data[CONF_PORT] == new_port
    assert (
        mock_plug_config_entry.unique_id == f"{new_host}:{new_port}:{UNIT_ID_PLUG}"
    )


async def test_options_flow_gateway_cannot_connect(
    hass: HomeAssistant,
    mock_gateway_config_entry: MockConfigEntry,
) -> None:
    """Test connection error surfaces when probing during gateway options update."""
    mock_gateway_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_gateway_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(
        mock_gateway_config_entry.entry_id
    )
    assert result["type"] is FlowResultType.FORM

    with patch(
        "custom_components.four_noks.config_flow.async_probe_device",
        side_effect=ModbusError("Unreachable"),
    ):
        result = await hass.config_entries.options.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "192.168.2.200",
                CONF_PORT: TEST_PORT,
                CONF_UNIT_ID: UNIT_ID_GATEWAY,
                CONF_SCAN_INTERVAL: 30,
                CONF_AUTO_DISCOVER: False,
            },
        )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_options_flow_gateway_already_configured(
    hass: HomeAssistant,
    mock_gateway_config_entry: MockConfigEntry,
    mock_plug_config_entry: MockConfigEntry,
) -> None:
    """Test already_configured error when changing gateway to match existing entry."""
    mock_gateway_config_entry.add_to_hass(hass)
    mock_plug_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_gateway_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(
        mock_gateway_config_entry.entry_id
    )
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: TEST_HOST,
            CONF_PORT: TEST_PORT,
            CONF_UNIT_ID: UNIT_ID_PLUG,
            CONF_SCAN_INTERVAL: 30,
            CONF_AUTO_DISCOVER: False,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "already_configured"}


async def test_options_flow_gateway_auto_discover(
    hass: HomeAssistant,
    mock_gateway_config_entry: MockConfigEntry,
) -> None:
    """Test auto_discover in options flow discovers nodes and shows list."""
    mock_gateway_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_gateway_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(
        mock_gateway_config_entry.entry_id
    )
    assert result["type"] is FlowResultType.FORM

    # UNIT_ID_PLUG (102) is unconfigured since mock_plug_config_entry is not added
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: TEST_HOST,
            CONF_PORT: TEST_PORT,
            CONF_UNIT_ID: UNIT_ID_GATEWAY,
            CONF_SCAN_INTERVAL: 20,
            CONF_AUTO_DISCOVER: True,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discover_nodes"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SELECTED_NODES: [str(UNIT_ID_PLUG)]},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_gateway_config_entry.options[CONF_SCAN_INTERVAL] == 20


async def test_reconfigure_flow_gateway(
    hass: HomeAssistant,
    mock_gateway_config_entry: MockConfigEntry,
    mock_plug_config_entry: MockConfigEntry,
) -> None:
    """Test reconfigure flow updates gateway and child plugs."""
    mock_gateway_config_entry.add_to_hass(hass)
    mock_plug_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_gateway_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await mock_gateway_config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    new_host = "192.168.2.88"
    new_port = 5022
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        user_input={
            CONF_HOST: new_host,
            CONF_PORT: new_port,
            CONF_UNIT_ID: UNIT_ID_GATEWAY,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_gateway_config_entry.data[CONF_HOST] == new_host
    assert mock_gateway_config_entry.data[CONF_PORT] == new_port
    assert (
        mock_gateway_config_entry.unique_id
        == f"{new_host}:{new_port}:{UNIT_ID_GATEWAY}"
    )

    # Verify child plug is also updated
    assert mock_plug_config_entry.data[CONF_HOST] == new_host
    assert mock_plug_config_entry.data[CONF_PORT] == new_port


async def test_reconfigure_flow_cannot_connect(
    hass: HomeAssistant,
    mock_gateway_config_entry: MockConfigEntry,
) -> None:
    """Test reconfigure flow surfaces cannot_connect on probe error."""
    mock_gateway_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_gateway_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await mock_gateway_config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    with patch(
        "custom_components.four_noks.config_flow.async_probe_device",
        side_effect=ModbusError("Connection failed"),
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            user_input={
                CONF_HOST: "192.168.2.77",
                CONF_PORT: TEST_PORT,
                CONF_UNIT_ID: UNIT_ID_GATEWAY,
            },
        )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}

