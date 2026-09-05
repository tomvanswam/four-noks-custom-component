"""Tests for 4-noks switch platform."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import DOMAIN as SWITCH_DOMAIN
from homeassistant.const import SERVICE_TURN_OFF, SERVICE_TURN_ON
from homeassistant.core import HomeAssistant
from modbus_connection.mock import MockModbusConnection
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def test_plug_switch_turn_on_off(
    hass: HomeAssistant,
    mock_plug_config_entry: MockConfigEntry,
    mock_modbus_connection: MockModbusConnection,
) -> None:
    """Test turning the plug switch on and off."""
    mock_plug_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_plug_config_entry.entry_id)
    await hass.async_block_till_done()

    switch_entity_id = "switch.zr_plug_m_102_switch"
    unit = mock_modbus_connection.for_unit(102)

    # Turn Off
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {"entity_id": switch_entity_id},
        blocking=True,
    )
    assert unit.coils[2] is True

    # Turn On
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {"entity_id": switch_entity_id},
        blocking=True,
    )
    assert unit.coils[1] is True


async def test_gateway_discovery_switch_turn_on_off(
    hass: HomeAssistant,
    mock_gateway_config_entry: MockConfigEntry,
    mock_modbus_connection: MockModbusConnection,
) -> None:
    """Test turning the gateway discovery switch on and off."""
    gw_unit = mock_modbus_connection.for_unit(1)

    # Listen for writes to simulate gateway DI 1 response to discovery commands
    def handle_gw_write(event: Any) -> None:
        if event.address == 0:
            if gw_unit.holding.get(0) == 5266:
                gw_unit.discrete_inputs[1] = True
            elif gw_unit.holding.get(0) == 5267:
                gw_unit.discrete_inputs[1] = False

    gw_unit.on_write(handle_gw_write)

    mock_gateway_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_gateway_config_entry.entry_id)
    await hass.async_block_till_done()

    switch_entity_id = "switch.zc_gw_eth_em_1_discovery"
    state = hass.states.get(switch_entity_id)
    assert state is not None
    assert state.state == "off"

    # Turn On (open discovery -> HR 0 = 5266, Coil 0 = True)
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_ON,
        {"entity_id": switch_entity_id},
        blocking=True,
    )
    assert gw_unit.holding[0] == 5266
    assert gw_unit.coils[0] is True
    assert hass.states.get(switch_entity_id).state == "on"

    # Turn Off (close discovery -> HR 0 = 5267, Coil 0 = True)
    await hass.services.async_call(
        SWITCH_DOMAIN,
        SERVICE_TURN_OFF,
        {"entity_id": switch_entity_id},
        blocking=True,
    )
    assert gw_unit.holding[0] == 5267
    assert gw_unit.coils[0] is True
    assert hass.states.get(switch_entity_id).state == "off"
