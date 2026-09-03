"""Subsystems for 4-noks Gateway (ZC-GW-ETH-EM)."""

from __future__ import annotations

from ..data_model import (
    FourNoksComponent,
    discrete_input,
    gauge,
    integer,
)


class GatewayRadio(FourNoksComponent):
    """Gateway wireless RF parameters, network counters, and diagnostic metrics."""

    register_space = "input"

    transmission_power = gauge(
        2, 1.0, offset=-100, unit="dB", description="RF Transmission Power"
    )
    network_channel = integer(
        3, signed=False, description="Zigbee Network Channel (11..26)"
    )
    network_panid = integer(4, signed=False, description="Network PAN ID")
    runtime = integer(5, signed=False, unit="s", description="Seconds From Last Reset")
    messages_received = integer(
        6, signed=False, description="Messages Received Counter"
    )
    node_count = integer(7, signed=False, description="Number of Used Agent Slots")
    gateway_address = integer(8, signed=False, description="Gateway Hardware Address")
    signal_level = gauge(
        11, 1.0, offset=-100, unit="dB", description="Gateway Wireless Signal Level"
    )
    bridge_devices_count = integer(
        12, signed=False, description="Devices Connected via Router-Bridge"
    )
    end_devices_count = integer(
        13, signed=False, description="End-Device Children of Gateway"
    )
    resets_count = integer(14, signed=False, description="Gateway Resets Counter")
    reset_type = integer(15, signed=False, description="Last Reset Cause")
    free_packet_buffer = integer(
        16, signed=False, description="Free Packet Buffers Count"
    )
    routers_total = integer(21, signed=False, description="Total Routers in Network")
    routers_neighbours = integer(
        22, signed=False, description="Total Router Neighbours"
    )
    routers_good = integer(23, signed=False, description="Good Router Neighbours")


class GatewayNetwork(FourNoksComponent):
    """Gateway network connectivity and discovery status."""

    register_space = "input"

    connection_state = discrete_input(
        0, description="Gateway Connected to Zigbee Network"
    )
    network_open_state = discrete_input(
        1, description="Network Open / Discovery Mode Active"
    )


class GatewaySettings(FourNoksComponent):
    """Configurable gateway parameters stored in holding registers."""

    register_space = "holding"

    working_mode = integer(
        3, signed=False, writable=True, description="Gateway Working Mode Flags"
    )
    absolute_time = integer(
        4, signed=False, writable=True, description="Absolute Clock Time (100*h + m)"
    )
    route_regeneration_period = integer(
        5,
        signed=False,
        writable=True,
        unit="s",
        description="MTOR Route Regeneration Period",
    )
    alternate_address = integer(
        10, signed=False, writable=True, description="Gateway Alternate Address"
    )
    bridge_min_address = integer(
        11,
        signed=False,
        writable=True,
        description="Router-Bridge Minimum Allowed Address",
    )
    bridge_max_address = integer(
        12,
        signed=False,
        writable=True,
        description="Router-Bridge Maximum Allowed Address",
    )
