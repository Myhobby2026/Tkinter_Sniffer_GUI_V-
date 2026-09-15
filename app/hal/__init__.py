"""Hardware Abstraction Layer (layer L1).

The desktop application contains NO Teensy-specific assumptions: it programs
against Device / CaptureDevice / DeviceCapabilities and works with any
implementation (Teensy, STM32, RP2040, FPGA, simulator — spec §14).
"""
from .capture_device import CaptureConfig, CaptureDevice
from .device import Device, DeviceCapabilities, DeviceInfo, DeviceState
from .device_manager import DeviceManager

__all__ = [
    "CaptureConfig",
    "CaptureDevice",
    "Device",
    "DeviceCapabilities",
    "DeviceInfo",
    "DeviceState",
    "DeviceManager",
]
