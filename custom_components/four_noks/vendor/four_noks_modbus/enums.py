"""Enums for 4-noks Modbus devices."""

from __future__ import annotations

from enum import IntEnum


class DeviceType(IntEnum):
    """4-noks device type reported in InputRegister[0]."""

    PLUG = 38  # 0x26 - ZR-PLUG-M / ZR-PLUG-EU-M Smart Plug
    GATEWAY = 112  # 0x70 - ZC-GW-ETH-EM Gateway Coordinator
    ROUTER_BRIDGE = 101  # 0x65 - ZR-BR-XX Router Bridge
    ROUTER_REPEATER = 108  # 0x6C - ZR-REP-XX Router Repeater


class ResetType(IntEnum):
    """Gateway reset cause reported in InputRegister[15]."""

    UNKNOWN = 0
    POWER_ON = 1
    EXTERNAL_PIN = 2
    WATCHDOG = 3
    SOFTWARE = 4


class WorkingModeBit(IntEnum):
    """Bit positions in Gateway Working Mode (HoldingRegister[3])."""

    TIMEOUT_MANAGEMENT = 0  # 0=access data in timeout, 1=no access/error
    EXCEPTION_RESPONSE = 1  # 0=no response on timeout, 1=exception 05
    ROUTER_BRIDGE_COMM = 2  # 0=enable broadcast for bridges, 1=disable
    HOLDING_REG_MODE = 3  # 0=sensor actual, 1=pending write values
    ROUTER_TABLE_ENABLE = 4  # 0=disable, 1=reserve 200-254 for router table
    SERIAL_RESPONSE_DELAY = 5  # 0=disable, 1=50ms delay
