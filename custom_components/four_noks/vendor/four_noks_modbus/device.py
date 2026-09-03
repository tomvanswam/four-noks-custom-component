"""Top-level 4-noks device objects and probe logic."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from .device_info import DeviceInformation
from .enums import DeviceType
from .subsystems.gateway import GatewayNetwork, GatewayRadio, GatewaySettings
from .subsystems.plug import PlugMeasurements, PlugSettings, PlugSwitch

if TYPE_CHECKING:
    from modbus_connection import ModbusUnit


class FourNoksDevice:
    """Base device representing a 4-noks Modbus unit."""

    def __init__(self, unit: ModbusUnit) -> None:
        self.unit = unit
        self.info = DeviceInformation(unit)

    async def async_update(self) -> None:
        """Poll the device and refresh its state."""
        await self.info.async_update()


class FourNoksPlug(FourNoksDevice):
    """A 4-noks ZR-PLUG-M / ZR-PLUG-EU-M smart plug and energy meter."""

    def __init__(self, unit: ModbusUnit) -> None:
        super().__init__(unit)
        self.measurements = PlugMeasurements(unit)
        self.switch = PlugSwitch(unit)
        self.settings = PlugSettings(unit)

    async def async_update(self) -> None:
        """Update all smart plug subsystems concurrently."""
        await asyncio.gather(
            self.info.async_update(),
            self.measurements.async_update(),
            self.switch.async_update(),
            self.settings.async_update(),
        )

    async def async_turn_on(self) -> None:
        """Turn on the plug relay."""
        await self.switch.async_turn_on()

    async def async_turn_off(self) -> None:
        """Turn off the plug relay."""
        await self.switch.async_turn_off()


class FourNoksGateway(FourNoksDevice):
    """A 4-noks ZC-GW-ETH-EM Ethernet Zigbee Gateway and Coordinator."""

    def __init__(self, unit: ModbusUnit) -> None:
        super().__init__(unit)
        self.radio = GatewayRadio(unit)
        self.network = GatewayNetwork(unit)
        self.settings = GatewaySettings(unit)

    async def async_update(self) -> None:
        """Update all gateway subsystems concurrently."""
        await asyncio.gather(
            self.info.async_update(),
            self.radio.async_update(),
            self.network.async_update(),
            self.settings.async_update(),
        )


async def async_probe_device(unit: ModbusUnit) -> FourNoksDevice:
    """Probe a Modbus unit to detect model and return device instance."""
    info = DeviceInformation(unit)
    await info.async_update()

    device_type = info.device_type_code
    if device_type == DeviceType.GATEWAY:
        device = FourNoksGateway(unit)
    elif device_type == DeviceType.PLUG:
        device = FourNoksPlug(unit)
    else:
        # Default / fallback: treat as Smart Plug if unknown or unconfigured
        device = FourNoksPlug(unit)

    device.info = info
    return device
