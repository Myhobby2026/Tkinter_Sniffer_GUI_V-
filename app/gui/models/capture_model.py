"""Capture status model (pure Python, thread-safe)."""
from __future__ import annotations

from dataclasses import dataclass, replace

from .observable import Observable


def _human_bytes(n: int) -> str:
    value = float(n)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024 or unit == "TB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{n} B"


@dataclass(frozen=True)
class CaptureStatus:
    state: str = "idle"
    block_count: int = 0
    byte_count: int = 0
    sample_rate_hz: int = 0
    channel_count: int = 0
    integrity_summary: str = "OK"
    last_error: str = ""

    def describe(self) -> str:
        base = f"Capture: {self.state}"
        if self.state in ("running", "stopped") and self.block_count:
            base += f" · {self.block_count} blocks · {_human_bytes(self.byte_count)}"
        return base


class CaptureModel(Observable):
    def __init__(self) -> None:
        super().__init__()
        self._status = CaptureStatus()

    def set(self, **fields: object) -> None:
        with self._lock:
            self._status = replace(self._status, **fields)  # type: ignore[arg-type]
            self._notify_locked()

    def reset(self) -> None:
        with self._lock:
            self._status = CaptureStatus()
            self._notify_locked()

    def snapshot(self) -> CaptureStatus:
        with self._lock:
            return replace(self._status)

    def describe(self) -> str:
        with self._lock:
            return self._status.describe()
