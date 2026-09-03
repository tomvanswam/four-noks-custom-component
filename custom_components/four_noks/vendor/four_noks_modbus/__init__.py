"""four-noks-modbus: communicate with 4-noks ZB-Connection Modbus devices.

Construct a device or use ``async_probe_device(unit)`` with a
``modbus_connection.ModbusUnit``, call ``await device.async_update()``,
then access subsystems and measurements directly:

    device.measurements.active_power
    device.measurements.energy_consumed_kwh
    device.switch.output_state
    await device.async_turn_on()
"""

from .addresses import (
    GATEWAY_DEFAULT_UNIT_ID,
    MAX_DEVICE_ADDRESS,
    MAX_SENSOR_ADDRESS,
    MIN_DEVICE_ADDRESS,
    MIN_SENSOR_ADDRESS,
    SMART_PLUG_DEFAULT_UNIT_ID,
)
from .data_model import FourNoksComponent
from .device import (
    FourNoksDevice,
    FourNoksGateway,
    FourNoksPlug,
    async_probe_device,
)
from .device_info import DeviceInformation
from .enums import DeviceType, ResetType, WorkingModeBit
from .exceptions import (
    FourNoksConnectionError,
    FourNoksDeviceTypeError,
    FourNoksError,
    FourNoksValueValidationError,
    FourNoksWriteError,
)
from .metadata import (
    DatapointMetadata,
    NumberMetadata,
    OptionMetadata,
)
from .subsystems import (
    GatewayNetwork,
    GatewayRadio,
    GatewaySettings,
    PlugMeasurements,
    PlugSettings,
    PlugSwitch,
)

__all__ = [
    "DatapointMetadata",
    "DeviceInformation",
    "DeviceType",
    "FourNoksComponent",
    "FourNoksConnectionError",
    "FourNoksDevice",
    "FourNoksDeviceTypeError",
    "FourNoksError",
    "FourNoksGateway",
    "FourNoksPlug",
    "FourNoksValueValidationError",
    "FourNoksWriteError",
    "GATEWAY_DEFAULT_UNIT_ID",
    "GatewayNetwork",
    "GatewayRadio",
    "GatewaySettings",
    "MAX_DEVICE_ADDRESS",
    "MAX_SENSOR_ADDRESS",
    "MIN_DEVICE_ADDRESS",
    "MIN_SENSOR_ADDRESS",
    "NumberMetadata",
    "OptionMetadata",
    "PlugMeasurements",
    "PlugSettings",
    "PlugSwitch",
    "ResetType",
    "SMART_PLUG_DEFAULT_UNIT_ID",
    "WorkingModeBit",
    "async_probe_device",
]
