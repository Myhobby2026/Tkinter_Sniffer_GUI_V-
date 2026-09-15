"""Device abstraction (spec §14/§15)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class DeviceState(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    FAULT = "fault"


@dataclass(frozen=True)
class DeviceInfo:
    """Static identity of a device."""

    name: str
    vendor_id: str
    product_id: str
    kind: str  # "teensy41", "simulator", "stm32", ...
    serial_number: str

    @property
    def id(self) -> str:
        return self.serial_number or self.name


@dataclass
class DeviceCapabilities:
    """Capabilities REPORTED by the device — the GUI enables features from here
    and nowhere else (spec §15).

    ``max_sample_rate_hz`` is the *measured/verified* rate. ``None`` means
    "unknown — never guess". The application must never display a rate it has
    not measured (spec §49).
    """

    channel_count: int = 0
    max_sample_rate_hz: int | None = None
    adc_channels: int = 0
    supported_protocols: tuple[str, ...] = ()
    supported_triggers: tuple[str, ...] = ()
    usb_speed: str = "unknown"
    firmware_version: str = "unknown"
    hardware_revision: str = "unknown"

    def to_dict(self) -> dict[str, Any]:
        return {
            "channel_count": self.channel_count,
            "max_sample_rate_hz": self.max_sample_rate_hz,
            "adc_channels": self.adc_channels,
            "supported_protocols": list(self.supported_protocols),
            "supported_triggers": list(self.supported_triggers),
            "usb_speed": self.usb_speed,
            "firmware_version": self.firmware_version,
            "hardware_revision": self.hardware_revision,
        }


class Device(ABC):
    """Base interface for any capture-capable hardware (or simulator)."""

    def __init__(self) -> None:
        self._state = DeviceState.DISCONNECTED

    @property
    def state(self) -> DeviceState:
        return self._state

    @property
    @abstractmethod
    def info(self) -> DeviceInfo:
        """Static identity."""

    @abstractmethod
    def capabilities(self) -> DeviceCapabilities:
        """Query live capabilities (spec §15). May be called after connect()."""

    @abstractmethod
    def connect(self) -> None:
        """Establish the link. Raises DeviceError on failure."""

    @abstractmethod
    def disconnect(self) -> None:
        """Tear down the link; idempotent."""

    def health(self) -> dict[str, Any]:
        """Lightweight liveness probe for the device panel (spec §40)."""
        return {"ok": self._state is DeviceState.CONNECTED, "state": self._state.value}
