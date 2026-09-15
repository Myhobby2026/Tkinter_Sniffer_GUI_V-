"""Capture manager: state machine + pipeline glue (device → integrity → storage).

Thread contract (spec §8):
    * ``_on_block`` may be invoked from ANY worker thread (simulator thread,
      transport reader thread in Phase 3) and is lock-guarded.
    * It never calls back into the GUI — the GUI observes state through the
      CaptureModel / UiEventQueue.

Phase 1 works with the simulator device; Phase 2/3 wire real firmware and the
USB transport behind the same interface.
"""
from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ...errors import CaptureError, DeviceError
from ..integrity import IntegrityReport, IntegrityTracker
from ..sample_block import CaptureBlock
from ..storage.capture_storage import CaptureStorage
from ...hal.capture_device import CaptureConfig, CaptureDevice
from ...hal.device import DeviceState


class CaptureState(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    STOPPED = "stopped"
    ERROR = "error"


@dataclass
class CaptureSummary:
    """Result of a completed capture (returned by CaptureManager.stop)."""

    state: str
    block_count: int
    byte_count: int
    sample_rate_hz: int
    channel_count: int
    integrity: IntegrityReport
    started_at: float | None = None
    ended_at: float | None = None

    @property
    def duration_seconds(self) -> float | None:
        if self.started_at is None or self.ended_at is None:
            return None
        return self.ended_at - self.started_at

    def to_dict(self) -> dict[str, Any]:
        return {
            "state": self.state,
            "block_count": self.block_count,
            "byte_count": self.byte_count,
            "sample_rate_hz": self.sample_rate_hz,
            "channel_count": self.channel_count,
            "integrity": self.integrity.to_dict(),
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_seconds": self.duration_seconds,
        }


class CaptureManager:
    """Coordinates capture device + storage + integrity.

    State machine:  IDLE → RUNNING → STOPPED   (errors surface via exceptions;
    the manager returns to IDLE on the next attach/configure cycle)
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._integrity = IntegrityTracker()
        self._device: CaptureDevice | None = None
        self._storage: CaptureStorage | None = None
        self._config: CaptureConfig | None = None
        self._state = CaptureState.IDLE
        self._blocks = 0
        self._bytes = 0
        self._started_at: float | None = None
        self._ended_at: float | None = None

    # ------------------------------------------------------------------ state
    @property
    def state(self) -> CaptureState:
        with self._lock:
            return self._state

    @property
    def device(self) -> CaptureDevice | None:
        with self._lock:
            return self._device

    @property
    def storage(self) -> CaptureStorage | None:
        with self._lock:
            return self._storage

    @property
    def config(self) -> CaptureConfig | None:
        with self._lock:
            return self._config

    @property
    def integrity_report(self) -> IntegrityReport:
        with self._lock:
            return self._integrity.report()

    def live_stats(self) -> dict[str, Any]:
        with self._lock:
            return {
                "state": self._state.value,
                "block_count": self._blocks,
                "byte_count": self._bytes,
            }

    # --------------------------------------------------------------- lifecycle
    def attach(self, device: CaptureDevice, storage: CaptureStorage) -> None:
        """Attach a (dis)connected capture device and the session storage."""
        with self._lock:
            if self._state is CaptureState.RUNNING:
                raise CaptureError(
                    "cannot attach while capturing", code="CAPTURE_ATTACH_RUNNING"
                )
            self._device = device
            self._storage = storage
            self._state = CaptureState.IDLE
            if self._config is not None:
                device.configure(self._config)

    def configure(self, config: CaptureConfig) -> None:
        with self._lock:
            if self._state is CaptureState.RUNNING:
                raise CaptureError(
                    "cannot reconfigure while capturing", code="CAPTURE_RECONFIG_RUNNING"
                )
            self._config = config
            if self._device is not None:
                self._device.configure(config)

    def start(self) -> None:
        with self._lock:
            if self._state is CaptureState.RUNNING:
                raise CaptureError("capture already running", code="CAPTURE_ALREADY_RUNNING")
            if self._device is None or self._storage is None:
                raise CaptureError(
                    "no device/storage attached", code="CAPTURE_NOT_ATTACHED"
                )
            if self._device.state is not DeviceState.CONNECTED:
                self._device.connect()
            self._integrity.reset()
            self._blocks = 0
            self._bytes = 0
            self._started_at = time.time()
            self._ended_at = None
            self._state = CaptureState.RUNNING
        # Start outside the lock: the device may immediately call _on_block,
        # which re-enters the manager.
        self._device.start_capture(self._on_block)

    def stop(self) -> CaptureSummary:
        with self._lock:
            if self._state is not CaptureState.RUNNING:
                raise CaptureError("not capturing", code="CAPTURE_NOT_RUNNING")
            self._state = CaptureState.STOPPED
        # stop_capture() may join a worker thread that calls _on_block; do it
        # without holding the lock. In-flight callbacks after STOPPED are
        # ignored (documented in _on_block).
        if self._device is not None:
            self._device.stop_capture()
        with self._lock:
            self._ended_at = time.time()
            report = self._integrity.report()
            assert self._config is not None
            summary = CaptureSummary(
                state=CaptureState.STOPPED.value,
                block_count=self._blocks,
                byte_count=self._bytes,
                sample_rate_hz=self._config.sample_rate_hz,
                channel_count=self._config.channel_count,
                integrity=report,
                started_at=self._started_at,
                ended_at=self._ended_at,
            )
            self._state = CaptureState.STOPPED
            return summary

    # ---------------------------------------------------------------- pipeline
    def _on_block(self, block: CaptureBlock) -> None:
        """Worker-thread entry point: integrity + storage. Never touches the GUI."""
        with self._lock:
            if self._state is not CaptureState.RUNNING:
                return
            self._integrity.feed(block)
            if self._storage is not None:
                self._storage.append(block)
            self._blocks += 1
            self._bytes += block.nbytes
