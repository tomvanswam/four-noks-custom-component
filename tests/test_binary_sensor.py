"""Tests for 4-noks binary sensor platform."""

from __future__ import annotations

from homeassistant.core import HomeAssistant

from tests.common import MockConfigEntry


async def test_unconfigured_device_presence_filtering(
    hass: HomeAssistant,
    mock_gateway_config_entry: MockConfigEntry,
    mock_plug_config_entry: MockConfigEntry,
) -> None:
    """Test unconfigured device presence filters out gateway and configured nodes."""
    # Add plug entry first so it exists in config entries
    mock_plug_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_plug_config_entry.entry_id)
    await hass.async_block_till_done()

    # Add gateway entry
    mock_gateway_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_gateway_config_entry.entry_id)
    await hass.async_block_till_done()

    sensor = hass.states.get(
        "binary_sensor.zc_gw_eth_em_1_unconfigured_device_presence"
    )
    assert sensor is not None
    assert sensor.state == "on"

    unconfigured = sensor.attributes.get("unconfigured_nodes", [])
    # Nodes 16 and 17 are seeded as present but unconfigured
    assert 16 in unconfigured
    assert 17 in unconfigured
    # Unit 102 is configured, so it must be filtered out
    assert 102 not in unconfigured
    # Unit 1 is the gateway itself, so it must not be in the list
    assert 1 not in unconfigured
    assert sensor.attributes.get("count") == len(unconfigured)


async def test_configured_child_node_presence_on_gateway(
    hass: HomeAssistant,
    mock_gateway_config_entry: MockConfigEntry,
    mock_plug_config_entry: MockConfigEntry,
) -> None:
    """Test gateway creates child node presence and data valid sensors."""
    mock_plug_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_plug_config_entry.entry_id)
    await hass.async_block_till_done()

    mock_gateway_config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(mock_gateway_config_entry.entry_id)
    await hass.async_block_till_done()

    # Child node 102 presence on gateway
    presence = hass.states.get("binary_sensor.zc_gw_eth_em_1_device_102_presence")
    assert presence is not None
    assert presence.state == "on"

    # Child node 102 data valid on gateway
    data_valid = hass.states.get("binary_sensor.zc_gw_eth_em_1_device_102_data_valid")
    assert data_valid is not None
    assert data_valid.state == "on"
