"""Device status model (pure Python, thread-safe)."""
from __future__ import annotations

from dataclasses import dataclass, replace

from .observable import Observable


@dataclass(frozen=True)
class DeviceStatus:
    device_id: str = ""
    name: str = ""
    state: str = "disconnected"
    firmware_version: str = ""
    hardware_revision: str = ""
    channel_count: int = 0

    @property
    def connected(self) -> bool:
        return self.state == "connected" and bool(self.device_id)

    def describe(self) -> str:
        if not self.device_id:
            return "Device: none"
        return f"Device: {self.name} ({self.firmware_version}) · {self.state}"


class DeviceModel(Observable):
    def __init__(self) -> None:
        super().__init__()
        self._status = DeviceStatus()

    def set_device(
        self,
        device_id: str,
        name: str,
        state: str,
        firmware_version: str = "",
        hardware_revision: str = "",
        channel_count: int = 0,
    ) -> None:
        with self._lock:
            self._status = DeviceStatus(
                device_id=device_id,
                name=name,
                state=state,
                firmware_version=firmware_version,
                hardware_revision=hardware_revision,
                channel_count=channel_count,
            )
            self._notify_locked()

    def clear(self) -> None:
        with self._lock:
            self._status = DeviceStatus()
            self._notify_locked()

    def snapshot(self) -> DeviceStatus:
        with self._lock:
            return replace(self._status)

    def describe(self) -> str:
        with self._lock:
            return self._status.describe()
