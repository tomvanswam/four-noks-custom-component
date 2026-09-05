"""Tests for the 4-noks config flow."""

from __future__ import annotations

from unittest.mock import patch

from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from modbus_connection import ModbusError
from modbus_connection.mock import MockModbusConnection
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.four_noks.const import (
    CONF_CONNECTION,
    CONF_UNIT_ID,
    DOMAIN,
)

from .conftest import UNIT_ID_GATEWAY, UNIT_ID_PLUG


async def test_user_flow_smart_plug(
    hass: HomeAssistant, connection_entry: MockConfigEntry
) -> None:
    """Selecting connection and plug unit probes the plug and creates the entry."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {CONF_CONNECTION: connection_entry.entry_id, CONF_UNIT_ID: UNIT_ID_PLUG},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"ZR-PLUG-M ({UNIT_ID_PLUG})"
    assert result["data"][CONF_CONNECTION] == connection_entry.entry_id
    assert result["data"][CONF_UNIT_ID] == UNIT_ID_PLUG


async def test_user_flow_gateway(
    hass: HomeAssistant, connection_entry: MockConfigEntry
) -> None:
    """Selecting connection and gateway unit probes and creates the entry."""
    from custom_components.four_noks.config_flow import CONF_AUTO_DISCOVER

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_CONNECTION: connection_entry.entry_id,
            CONF_UNIT_ID: UNIT_ID_GATEWAY,
            CONF_AUTO_DISCOVER: False,
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == f"ZC-GW-ETH-EM ({UNIT_ID_GATEWAY})"
    assert result["data"][CONF_CONNECTION] == connection_entry.entry_id
    assert result["data"][CONF_UNIT_ID] == UNIT_ID_GATEWAY


async def test_user_flow_gateway_discovery_step(
    hass: HomeAssistant, connection_entry: MockConfigEntry
) -> None:
    """Gateway flow with auto_discover shows discovery step."""
    from custom_components.four_noks.config_flow import CONF_AUTO_DISCOVER

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_CONNECTION: connection_entry.entry_id,
            CONF_UNIT_ID: UNIT_ID_GATEWAY,
            CONF_AUTO_DISCOVER: True,
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "discover_nodes"


async def test_user_flow_cannot_connect(
    hass: HomeAssistant,
    connection_entry: MockConfigEntry,
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
            {CONF_CONNECTION: connection_entry.entry_id, CONF_UNIT_ID: UNIT_ID_PLUG},
        )
        assert result["type"] is FlowResultType.FORM
        assert result["errors"] == {"base": "cannot_connect"}


async def test_options_flow(
    hass: HomeAssistant,
    mock_plug_config_entry: MockConfigEntry,
) -> None:
    """Test options flow to configure custom polling scan interval."""
    mock_plug_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_plug_config_entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.options.async_init(
        mock_plug_config_entry.entry_id
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        user_input={CONF_SCAN_INTERVAL: 15},
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert mock_plug_config_entry.options[CONF_SCAN_INTERVAL] == 15
