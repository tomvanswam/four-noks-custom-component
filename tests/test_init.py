"""Tests for 4-noks integration setup and unload."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry


async def _setup(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()


async def test_setup_plug_creates_entities(
    hass: HomeAssistant, mock_plug_config_entry: MockConfigEntry
) -> None:
    """The smart plug entry loads and produces switch, sensor, and binary sensors."""
    await _setup(hass, mock_plug_config_entry)
    assert mock_plug_config_entry.state is ConfigEntryState.LOADED

    # Check Switch
    switch = hass.states.get("switch.zr_plug_m_102_switch")
    assert switch is not None
    assert switch.state == "on"

    # Check Sensors
    power = hass.states.get("sensor.zr_plug_m_102_active_power")
    assert power is not None
    assert power.state == "2350"

    energy = hass.states.get("sensor.zr_plug_m_102_energy_consumed")
    assert energy is not None
    assert float(energy.state) == 70.968

    signal = hass.states.get("sensor.zr_plug_m_102_radio_signal_level")
    assert signal is not None
    assert signal.state == "35"

    # Check Binary Sensor
    presence = hass.states.get("binary_sensor.zr_plug_m_102_presence")
    assert presence is not None
    assert presence.state == "on"

    # Check Button
    reset_button = hass.states.get("button.zr_plug_m_102_enable_standby_killer")
    assert reset_button is not None


async def test_setup_gateway_creates_entities(
    hass: HomeAssistant, mock_gateway_config_entry: MockConfigEntry
) -> None:
    """The gateway entry loads and produces sensors, switches, and binary sensors."""
    await _setup(hass, mock_gateway_config_entry)
    assert mock_gateway_config_entry.state is ConfigEntryState.LOADED

    # Consolidated Nodes Sensor
    nodes = hass.states.get("sensor.zc_gw_eth_em_1_nodes")
    assert nodes is not None
    assert nodes.state == "5"
    assert nodes.attributes.get("bridge_end_devices") == 0
    assert nodes.attributes.get("local_end_devices") == 2
    assert nodes.attributes.get("routers_total") == 17

    # Consolidated Routers Sensor
    routers = hass.states.get("sensor.zc_gw_eth_em_1_routers")
    assert routers is not None
    assert routers.state == "17"
    assert routers.attributes.get("good_router_neighbours") == 3
    assert routers.attributes.get("router_neighbours") == 16

    # Discovery Switch
    discovery = hass.states.get("switch.zc_gw_eth_em_1_discovery")
    assert discovery is not None
    assert discovery.state == "off"

    # Gateway Network Connected Binary Sensor
    conn_state = hass.states.get("binary_sensor.zc_gw_eth_em_1_network_connected")
    assert conn_state is not None
    assert conn_state.state == "on"

    # Unconfigured Device Presence Binary Sensor
    unconfigured = hass.states.get(
        "binary_sensor.zc_gw_eth_em_1_unconfigured_device_presence"
    )
    assert unconfigured is not None
    assert unconfigured.state == "on"
    assert 16 in unconfigured.attributes.get("unconfigured_nodes", [])
    assert 17 in unconfigured.attributes.get("unconfigured_nodes", [])


async def test_unload_entry(
    hass: HomeAssistant, mock_plug_config_entry: MockConfigEntry
) -> None:
    """Test unloading a config entry."""
    await _setup(hass, mock_plug_config_entry)
    assert mock_plug_config_entry.state is ConfigEntryState.LOADED

    assert await hass.config_entries.async_unload(mock_plug_config_entry.entry_id)
    await hass.async_block_till_done()
    assert mock_plug_config_entry.state is ConfigEntryState.NOT_LOADED


async def test_legacy_entry_migration(
    hass: HomeAssistant,
) -> None:
    """Test legacy config entry without host/port auto-migrates."""
    legacy_conn = MockConfigEntry(
        domain="modbus_connection",
        data={"host": "192.168.2.3", "port": 502},
        entry_id="legacy_conn_123",
    )
    legacy_conn.add_to_hass(hass)

    legacy_entry = MockConfigEntry(
        domain="four_noks",
        data={"connection": "legacy_conn_123", "unit_id": 102},
        unique_id="legacy_conn_123_102",
        title="ZR-PLUG-M (102)",
    )
    await _setup(hass, legacy_entry)
    assert legacy_entry.state is ConfigEntryState.LOADED
    assert legacy_entry.data["host"] == "192.168.2.3"
    assert legacy_entry.data["port"] == 502
    assert legacy_entry.data["unit_id"] == 102
    assert legacy_entry.unique_id == "192.168.2.3:502:102"
