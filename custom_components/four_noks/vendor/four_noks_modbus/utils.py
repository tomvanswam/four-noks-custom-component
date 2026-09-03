"""Utility functions for four-noks-modbus."""

from __future__ import annotations


def parse_time_hhmm(raw: int) -> tuple[int, int]:
    """Parse a packed time word (100 * hour + minute) into (hour, minute)."""
    hour = raw // 100
    minute = raw % 100
    return hour, minute


def format_time_hhmm(hour: int, minute: int) -> int:
    """Format hour and minute into packed time word (100 * hour + minute)."""
    return hour * 100 + minute


unpack_packed_time = parse_time_hhmm
pack_packed_time = format_time_hhmm
