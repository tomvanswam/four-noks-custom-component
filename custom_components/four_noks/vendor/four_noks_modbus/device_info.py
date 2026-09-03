"""Device identity and firmware version component for 4-noks devices."""

from __future__ import annotations

from .data_model import FourNoksComponent, integer
from .enums import DeviceType


def format_firmware_version(raw: int | None) -> str | None:
    """Format firmware version word into major.minor string.

    4-noks firmware versions are typically encoded as:
    2053 -> 20.53, 748 -> 7.48.
    """
    if raw is None:
        return None
    major = raw // 100
    minor = raw % 100
    return f"{major}.{minor:02d}"


class DeviceInformation(FourNoksComponent):
    """Component reading common device identification and firmware version."""

    register_space = "input"

    _device_type_raw = integer(0, signed=False, description="Device Type Code")
    _firmware_raw = integer(1, signed=False, description="Firmware Version")

    @property
    def manufacturer(self) -> str:
        """Device manufacturer name."""
        return "4-noks"

    @property
    def device_type_code(self) -> int | None:
        """Raw device type identifier reported in InputRegister[0]."""
        return self._device_type_raw

    @property
    def firmware_version(self) -> str | None:
        """Parsed firmware version string (e.g. '20.53')."""
        return format_firmware_version(self._firmware_raw)

    @property
    def model(self) -> str:
        """Human-readable model name."""
        code = self.device_type_code
        if code == DeviceType.PLUG:
            return "ZR-PLUG-M"
        if code == DeviceType.GATEWAY:
            return "ZC-GW-ETH-EM"
        if code == DeviceType.ROUTER_BRIDGE:
            return "ZR-BR-XX"
        if code == DeviceType.ROUTER_REPEATER:
            return "ZR-REP-XX"
        return f"4-noks Device ({code})" if code is not None else "4-noks Device"
