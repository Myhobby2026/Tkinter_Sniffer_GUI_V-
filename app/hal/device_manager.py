"""Device manager: registry + lifecycle (spec §40; discovery lands with the
USB transport in Phase 3)."""
from __future__ import annotations

import threading
from typing import Callable

from ..errors import DeviceError
from .device import Device, DeviceInfo, DeviceState


class DeviceManager:
    """Tracks known devices and their lifecycle.

    Phase 1 devices are registered explicitly (the built-in simulator).
    Phase 3 adds USB enumeration behind the same API.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._devices: dict[str, Device] = {}
        self._listeners: list[Callable[[str, str], None]] = []

    # ------------------------------------------------------------- registry
    def register(self, device: Device) -> None:
        with self._lock:
            device_id = device.info.id
            if device_id in self._devices:
                raise DeviceError(
                    f"device '{device_id}' already registered", code="DEVICE_DUP"
                )
            self._devices[device_id] = device

    def unregister(self, device_id: str) -> None:
        with self._lock:
            self._devices.pop(device_id, None)

    def get(self, device_id: str) -> Device:
        with self._lock:
            try:
                return self._devices[device_id]
            except KeyError:
                raise DeviceError(
                    f"unknown device '{device_id}'", code="DEVICE_NOT_FOUND"
                ) from None

    def list_devices(self) -> list[DeviceInfo]:
        with self._lock:
            return [device.info for device in self._devices.values()]

    def devices(self) -> list[tuple[DeviceInfo, DeviceState]]:
        with self._lock:
            return [(d.info, d.state) for d in self._devices.values()]

    # ------------------------------------------------------------ lifecycle
    def connect(self, device_id: str) -> Device:
        device = self.get(device_id)
        device.connect()
        self._emit(device_id, device.state.value)
        return device

    def disconnect(self, device_id: str) -> None:
        device = self.get(device_id)
        device.disconnect()
        self._emit(device_id, device.state.value)

    # -------------------------------------------------------------- events
    def on_state_change(self, callback: Callable[[str, str], None]) -> None:
        """callback(device_id, state) — invoked on the thread that changed it."""
        with self._lock:
            self._listeners.append(callback)

    def _emit(self, device_id: str, state: str) -> None:
        with self._lock:
            listeners = list(self._listeners)
        for callback in listeners:
            callback(device_id, state)
