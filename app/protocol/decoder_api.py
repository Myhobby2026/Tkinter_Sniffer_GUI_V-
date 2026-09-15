"""Protocol decoder API (spec §16/§17, see docs/decoder_api.md).

Rules:
    * Decoders are streaming: feed SampleBatch, receive DecodedEvents.
    * All times are integer sample indices on the master timeline.
    * Decoders NEVER reference Tkinter, transports, or storage.
    * API is versioned; the registry rejects incompatible majors.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ..core.sample_block import SampleBatch

DECODER_API_VERSION = "1.0"


def api_version_compatible(a: str, b: str) -> bool:
    """Same major version → compatible (semver-style for decoder APIs)."""
    try:
        return a.split(".")[0] == b.split(".")[0]
    except (AttributeError, IndexError):
        return False


@dataclass(frozen=True)
class DecoderInfo:
    """Static metadata exposed by every decoder (used by the registry and UI)."""

    id: str                    # stable identifier, e.g. "spi"
    name: str                  # display name, e.g. "SPI"
    api_version: str           # decoder API version this decoder implements
    version: str               # decoder implementation version
    description: str = ""
    required_channels: tuple[str, ...] = ()   # logical channel names
    config_defaults: dict[str, Any] = field(default_factory=dict)


class DecoderStatus(str, Enum):
    OK = "ok"
    WARNING = "warning"   # decoded, with timing/protocol anomalies
    ERROR = "error"       # could not decode reliably


@dataclass
class DecodedEvent:
    """Structured decoder output consumed by the GUI (spec §17)."""

    protocol: str                      # decoder id, e.g. "spi"
    event_type: str                    # e.g. "tx_word", "start", "data", "stop"
    start_index: int                   # master-timeline sample index
    duration: int = 0                  # in samples
    channel: str | None = None         # logical channel name (from mapping)
    fields: dict[str, Any] = field(default_factory=dict)
    payload: bytes | None = None
    text: str = ""                     # human-readable summary
    status: DecoderStatus = DecoderStatus.OK
    errors: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "protocol": self.protocol,
            "event_type": self.event_type,
            "start_index": self.start_index,
            "duration": self.duration,
            "channel": self.channel,
            "fields": self.fields,
            "payload": self.payload.hex() if self.payload is not None else None,
            "text": self.text,
            "status": self.status.value,
            "errors": list(self.errors),
        }


class ProtocolDecoder(ABC):
    """Streaming protocol decoder (spec §16)."""

    @property
    @abstractmethod
    def info(self) -> DecoderInfo:
        """Static metadata."""

    @abstractmethod
    def configure(self, config: dict[str, Any]) -> None:
        """Apply configuration (must include channel mapping). Raises DecoderError."""

    @abstractmethod
    def reset(self) -> None:
        """Clear internal state; must be callable at any time."""

    @abstractmethod
    def process(self, batch: "SampleBatch") -> list[DecodedEvent]:
        """Consume one batch; return events in sample-index order."""

    def flush(self) -> list[DecodedEvent]:
        """Emit buffered events at end-of-stream (default: nothing buffered)."""
        return []
