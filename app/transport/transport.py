"""Transport abstraction (spec §10).

A Transport is a bidirectional link to a capture device. The USB CDC / HS
implementations land in Phase 3; this contract is what the rest of the
application programs against today.

Threading contract (spec §8):
    * ``open()`` may block (device enumeration) — call it from a worker
      thread, never the GUI thread.
    * After ``open()``, the transport produces :class:`TransportEvent` items
      on its own worker thread; consumers ``drain_events()`` non-blocking.
    * ``send_command()`` is non-blocking with a bounded outbox; backpressure
      raises USBError — commands are never silently dropped.
"""
from __future__ import annotations

import queue
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from ..errors import USBError


class TransportState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    DEGRADED = "degraded"  # link up but losing data (overflow/retry)
    FAULT = "fault"


class TransportEventKind(str, Enum):
    BLOCK = "block"            # data: CaptureBlock
    DEVICE_STATUS = "status"   # data: dict (state, heartbeat, throughput)
    ERROR = "error"            # data: SnifferError.to_dict()
    CLOSED = "closed"          # data: None (reason in context if provided)


@dataclass
class TransportEvent:
    kind: TransportEventKind
    data: Any = None


class Transport(ABC):
    """A bidirectional link to a capture device."""

    def __init__(self, name: str = "") -> None:
        self._name = name or self.__class__.__name__
        self._state = TransportState.CLOSED
        self._events: "queue.Queue[TransportEvent]" = queue.Queue()

    @property
    def name(self) -> str:
        return self._name

    @property
    def state(self) -> TransportState:
        return self._state

    # ------------------------------------------------------------- lifecycle
    @abstractmethod
    def open(self, options: dict[str, Any] | None = None) -> None:
        """Establish the link. Raises USBError on failure."""

    @abstractmethod
    def close(self) -> None:
        """Tear down the link; posts a CLOSED event; idempotent."""

    @abstractmethod
    def send_command(self, command: bytes) -> None:
        """Queue a command frame (non-blocking). Raises USBError on backpressure."""

    # -------------------------------------------------------------- events
    @property
    def events(self) -> "queue.Queue[TransportEvent]":
        """The underlying queue (blocking gets reserved for pipeline workers)."""
        return self._events

    def post_event(self, event: TransportEvent) -> None:
        """Called by the transport's worker thread; safe from any thread."""
        self._events.put(event)

    def drain_events(self, max_events: int = 256) -> list[TransportEvent]:
        """Non-blocking drain for the ingest worker / UI bridge."""
        out: list[TransportEvent] = []
        while len(out) < max_events:
            try:
                out.append(self._events.get_nowait())
            except queue.Empty:
                return out
        return out
