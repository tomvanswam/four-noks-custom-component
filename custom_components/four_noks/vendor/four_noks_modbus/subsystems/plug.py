"""Subsystems for 4-noks Smart Plugs (ZR-PLUG-M / ZR-PLUG-EU-M)."""

from __future__ import annotations

from ..data_model import (
    FourNoksComponent,
    coil,
    discrete_input,
    gauge,
    integer,
    uint32,
)


class PlugMeasurements(FourNoksComponent):
    """Real-time physical measurements and communications telemetry."""

    register_space = "input"

    # Radio & Diagnostics
    messages_sent = integer(2, signed=False, description="Messages Sent Counter")
    signal_level_radio = gauge(
        3, 1.0, offset=-100, unit="dB", description="Radio Signal Level"
    )
    calibration_parameter = integer(
        4, signed=False, description="Energy Meter Calibration Parameter"
    )

    # Electrical Measurements
    active_power = gauge(5, 1.0, signed=False, unit="W", description="Active Power")
    _energy_consumed_wh_raw = uint32(
        6, word_order="little", unit="Wh", description="Energy Consumed (Wh)"
    )
    measure_time = uint32(
        8, word_order="little", unit="s", description="Measurement Time (seconds)"
    )

    # Gateway Agent Telemetry
    gw_sec_last_message = integer(
        10, signed=False, unit="s", description="Seconds Since Last Message"
    )
    gw_messages_received = integer(
        11, signed=False, description="Messages Received from Device"
    )
    gw_message_receiving_instant_time = integer(
        12,
        signed=False,
        description="Gateway Message Receiving Instant Time (Packed HH:MM)",
    )
    gw_last_message_signal_lvl = gauge(
        13, 1.0, offset=-100, unit="dB", description="Gateway Received Signal Level"
    )
    gw_device_network_address = integer(
        14, signed=False, description="Device Network Address"
    )

    @property
    def gw_message_receiving_instant_time_formatted(self) -> str | None:
        """Formatted reception time as HH:MM."""
        if self.gw_message_receiving_instant_time is None:
            return None
        from ..utils import unpack_packed_time

        hour, minute = unpack_packed_time(self.gw_message_receiving_instant_time)
        return f"{hour:02d}:{minute:02d}"

    @property
    def energy_consumed_wh(self) -> float | None:
        """Total cumulative energy consumed in Wh."""
        return (
            float(self._energy_consumed_wh_raw)
            if self._energy_consumed_wh_raw is not None
            else None
        )

    @property
    def energy_consumed_kwh(self) -> float | None:
        """Total cumulative energy consumed converted to kWh."""
        val = self.energy_consumed_wh
        return val / 1000.0 if val is not None else None


class PlugSwitch(FourNoksComponent):
    """Relay control, stand-by killer status, and device presence."""

    register_space = "input"

    output_state = discrete_input(0, description="Output State (Relay ON/OFF)")
    standby_killer_status = discrete_input(1, description="Standby Killer Status")
    presence = discrete_input(64, description="Device Presence Status")
    general_pending = discrete_input(65, description="General Pending Status")

    # Command coils (FC 05)
    _turn_on_coil = coil(1, writable=True, description="Switch ON Command")
    _turn_off_coil = coil(2, writable=True, description="Switch OFF Command")
    _standby_killer_coil = coil(
        3, writable=True, description="Standby Killer Enable Command"
    )
    _data_reset_coil = coil(
        4, writable=True, description="Reset Measurement Data Command"
    )
    _data_save_coil = coil(
        5, writable=True, description="Save Data to Non-Volatile Memory Command"
    )

    async def async_turn_on(self) -> None:
        """Turn on the plug relay via coil 1."""
        await self.write("_turn_on_coil", True)

    async def async_turn_off(self) -> None:
        """Turn off the plug relay via coil 2."""
        await self.write("_turn_off_coil", True)

    async def async_enable_standby_killer(self) -> None:
        """Enable standby killer and switch on load via coil 3."""
        await self.write("_standby_killer_coil", True)

    async def async_reset_data(self) -> None:
        """Reset measurement counters to zero via coil 4."""
        await self.write("_data_reset_coil", True)

    async def async_save_data(self) -> None:
        """Save data to non-volatile flash via coil 5."""
        await self.write("_data_save_coil", True)


class PlugSettings(FourNoksComponent):
    """Configurable device parameters stored in non-volatile holding registers."""

    register_space = "holding"

    transmission_time = integer(
        1, signed=False, writable=True, unit="s", description="Transmission Period"
    )
    standby_killer_time_window = integer(
        3,
        signed=False,
        writable=True,
        unit="s",
        description="Standby Killer Time Window",
    )
    standby_killer_power_threshold = integer(
        4,
        signed=False,
        writable=True,
        unit="W",
        description="Standby Killer Power Threshold",
    )
