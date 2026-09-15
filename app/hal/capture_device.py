"""Capture device interface + capture configuration (spec §14).

``CaptureConfig`` lives here (not in core) so the HAL stays self-contained;
core.capture re-uses it.
"""
from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable

from ..errors import CaptureError
from .device import Device

if TYPE_CHECKING:
    from ..core.sample_block import CaptureBlock
    from ..trigger.trigger_api import TriggerSpec


@dataclass
class CaptureConfig:
    """Device-level capture configuration."""

    sample_rate_hz: int
    channel_count: int
    channel_mask: int | None = None  # None → first N channels
    trigger: "TriggerSpec | None" = None

    def __post_init__(self) -> None:
        rate = int(self.sample_rate_hz)
        if rate <= 0:
            raise CaptureError("sample_rate_hz must be positive", code="CAPTURE_BAD_RATE")
        if not 1 <= int(self.channel_count) <= 16:
            raise CaptureError("channel_count must be 1..16", code="CAPTURE_BAD_CHANNELS")
        if self.channel_mask is not None and not 0 < int(self.channel_mask) <= 0xFFFF:
            raise CaptureError("channel_mask must be 0x0001..0xFFFF", code="CAPTURE_BAD_MASK")

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_rate_hz": self.sample_rate_hz,
            "channel_count": self.channel_count,
            "channel_mask": self.channel_mask,
            "trigger": self.trigger.to_dict() if self.trigger is not None else None,
        }


class CaptureDevice(Device):
    """A Device that can capture digital samples (spec §14).

    Block callback contract:
        * ``start_capture(cb)`` returns immediately; ``cb(block)`` is invoked
          from the device's worker thread, in sequence order, from seq 0.
        * ``stop_capture()`` returns only after the device guarantees no
          further callbacks will fire (simulator: thread joined; hardware:
          end-of-stream block delivered or loss flagged).
    """

    @abstractmethod
    def configure(self, config: CaptureConfig) -> None:
        """Apply configuration. Must be rejected while capturing."""

    @abstractmethod
    def start_capture(self, block_callback: Callable[[CaptureBlock], None]) -> None:
        """Begin capturing; blocks flow through ``block_callback``."""

    @abstractmethod
    def stop_capture(self) -> None:
        """Stop capturing; guarantees no further callbacks after return."""

    @property
    @abstractmethod
    def capture_state(self) -> str:
        """Device-side capture state: "idle" | "running" | "error"."""
