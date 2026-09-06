"""Tests for 4-noks sensor platform."""

from __future__ import annotations

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from tests.common import MockConfigEntry


async def test_gateway_consolidated_sensors(
    hass: HomeAssistant,
    mock_gateway_config_entry: MockConfigEntry,
) -> None:
    """Test the consolidated Nodes and Routers sensors on the Gateway."""
    mock_gateway_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_gateway_config_entry.entry_id)
    await hass.async_block_till_done()

    ent_reg = er.async_get(hass)

    # 1. Nodes sensor
    nodes_state = hass.states.get("sensor.zc_gw_eth_em_1_nodes")
    assert nodes_state is not None
    assert nodes_state.state == "5"
    assert nodes_state.attributes.get("bridge_end_devices") == 0
    assert nodes_state.attributes.get("local_end_devices") == 2
    assert nodes_state.attributes.get("routers_total") == 17

    nodes_entry = ent_reg.async_get("sensor.zc_gw_eth_em_1_nodes")
    assert nodes_entry is not None
    assert nodes_entry.entity_category is None

    # 2. Routers sensor
    routers_state = hass.states.get("sensor.zc_gw_eth_em_1_routers")
    assert routers_state is not None
    assert routers_state.state == "17"
    assert routers_state.attributes.get("good_router_neighbours") == 3
    assert routers_state.attributes.get("router_neighbours") == 16

    routers_entry = ent_reg.async_get("sensor.zc_gw_eth_em_1_routers")
    assert routers_entry is not None
    assert routers_entry.entity_category is None


async def test_plug_sensors(
    hass: HomeAssistant,
    mock_plug_config_entry: MockConfigEntry,
) -> None:
    """Test smart plug telemetry sensors."""
    mock_plug_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_plug_config_entry.entry_id)
    await hass.async_block_till_done()

    power = hass.states.get("sensor.zr_plug_m_102_active_power")
    assert power is not None
    assert power.state == "2350"

    energy = hass.states.get("sensor.zr_plug_m_102_energy_consumed")
    assert energy is not None
    assert float(energy.state) == 70.968

    signal = hass.states.get("sensor.zr_plug_m_102_radio_signal_level")
    assert signal is not None
    assert signal.state == "35"
