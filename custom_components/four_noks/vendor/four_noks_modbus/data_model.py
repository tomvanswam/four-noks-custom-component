"""Data model base classes and field definitions for 4-noks devices."""

from __future__ import annotations

from typing import Any

from modbus_connection.model import (
    Component,
    coil as _modbus_coil,
    discrete_input as _modbus_discrete_input,
    gauge as _modbus_gauge,
    integer as _modbus_integer,
    uint32 as _modbus_uint32,
)

from .metadata import (
    DatapointMetadata,
    NumberMetadata,
    attach_metadata,
)


class FourNoksComponent(Component):
    """Base component for 4-noks device subsystems."""

    max_gap = 16
    max_span = 125


def integer(
    address: int,
    *,
    signed: bool = True,
    unit: str | None = None,
    writable: bool = False,
    description: str | None = None,
    min_value: int | None = None,
    max_value: int | None = None,
    **kwargs: Any,
) -> Any:
    """Define a 16-bit integer register field with metadata."""
    field = _modbus_integer(
        address,
        signed=signed,
        unit=unit,
        writable=writable,
        **kwargs,
    )
    return attach_metadata(
        field,
        DatapointMetadata(
            value_kind="number",
            description=description,
            writable=writable,
            number=NumberMetadata(
                min_value=min_value,
                max_value=max_value,
                step=1,
                digits=0,
                unit=unit,
            ),
        ),
    )


def gauge(
    address: int,
    scale: float,
    *,
    offset: float = 0.0,
    signed: bool = True,
    unit: str | None = None,
    writable: bool = False,
    description: str | None = None,
    digits: int = 2,
    min_value: float | None = None,
    max_value: float | None = None,
    **kwargs: Any,
) -> Any:
    """Define a scaled float gauge register field with metadata."""
    field = _modbus_gauge(
        address,
        scale,
        offset=offset,
        signed=signed,
        unit=unit,
        writable=writable,
        **kwargs,
    )
    return attach_metadata(
        field,
        DatapointMetadata(
            value_kind="number",
            description=description,
            writable=writable,
            number=NumberMetadata(
                min_value=min_value,
                max_value=max_value,
                digits=digits,
                unit=unit,
            ),
        ),
    )


def uint32(
    address: int,
    *,
    scale: float = 1.0,
    word_order: str = "little",
    unit: str | None = None,
    description: str | None = None,
    **kwargs: Any,
) -> Any:
    """Define a 32-bit unsigned integer register field with metadata."""
    field = _modbus_uint32(
        address,
        scale=scale,
        word_order=word_order,  # type: ignore[arg-type]
        unit=unit,
        **kwargs,
    )
    return attach_metadata(
        field,
        DatapointMetadata(
            value_kind="number",
            description=description,
            writable=False,
            number=NumberMetadata(unit=unit),
        ),
    )


def coil(
    address: int,
    *,
    writable: bool = True,
    description: str | None = None,
    **kwargs: Any,
) -> Any:
    """Define a Modbus coil field with metadata."""
    field = _modbus_coil(address, writable=writable, **kwargs)
    return attach_metadata(
        field,
        DatapointMetadata(
            value_kind="boolean",
            description=description,
            writable=writable,
        ),
    )


def discrete_input(
    address: int,
    *,
    description: str | None = None,
    **kwargs: Any,
) -> Any:
    """Define a discrete input field with metadata."""
    field = _modbus_discrete_input(address, **kwargs)
    return attach_metadata(
        field,
        DatapointMetadata(
            value_kind="boolean",
            description=description,
            writable=False,
        ),
    )
