"""Exceptions raised by four-noks-modbus."""

from __future__ import annotations


class FourNoksError(Exception):
    """Base exception for all four-noks-modbus errors."""


class FourNoksConnectionError(FourNoksError):
    """Raised when Modbus communication fails."""


class FourNoksDeviceTypeError(FourNoksError):
    """Raised when an unrecognized or unsupported 4-noks device type is encountered."""


class FourNoksWriteError(FourNoksError):
    """Raised when a write operation fails or is rejected."""


class FourNoksValueValidationError(FourNoksError, ValueError):
    """Raised when a value is outside its allowed domain."""
