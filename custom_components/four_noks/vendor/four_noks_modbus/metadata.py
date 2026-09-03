"""Datapoint metadata for 4-noks Modbus fields."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

ValueKind = Literal["number", "boolean", "enum", "string"]


@dataclass(frozen=True)
class NumberMetadata:
    """Metadata for numeric 4-noks datapoints."""

    min_value: float | int | None = None
    max_value: float | int | None = None
    step: float | int | None = None
    digits: int | None = None
    unit: str | None = None


@dataclass(frozen=True)
class OptionMetadata:
    """Metadata for one option in an enumeration."""

    key: str
    value: int
    label: str | None = None


@dataclass(frozen=True)
class DatapointMetadata:
    """Attached metadata describing a field."""

    value_kind: ValueKind
    description: str | None = None
    writable: bool = False
    number: NumberMetadata | None = None
    options: tuple[OptionMetadata, ...] = ()


def attach_metadata(field: Any, metadata: DatapointMetadata) -> Any:
    """Attach metadata to a modbus_connection RegisterField."""
    field._four_noks_metadata = metadata
    return field


def get_metadata(field: Any) -> DatapointMetadata | None:
    """Retrieve metadata attached to a field."""
    return getattr(field, "_four_noks_metadata", None)
