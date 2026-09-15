"""Thread-safe UI event channel (spec §8).

Workers post UiEvents; the GUI thread drains them in its poll loop. No
Tkinter import here — this module is pure Python and unit-testable.
"""
from __future__ import annotations

import queue
from dataclasses import dataclass, field
from typing import Any


# Event kinds
EVENT_STATUS = "status"          # status-bar fields
EVENT_DEVICE = "device_update"   # device list/state changed
EVENT_CAPTURE = "capture_update"  # capture progress changed
EVENT_MESSAGE = "message"        # transient message: data={"text": str}
EVENT_ERROR = "error"            # structured error: data=SnifferError.to_dict()
EVENT_THEME = "theme"            # theme change: data={"theme": str}
EVENT_LOG = "log"                # debug log line: data={"text": str}


@dataclass
class UiEvent:
    kind: str
    data: dict[str, Any] = field(default_factory=dict)


class UiEventQueue:
    """Bounded-ish queue of UI events. ``post`` is safe from any thread;
    only the GUI thread should call ``drain``/``clear``."""

    def __init__(self) -> None:
        self._q: "queue.Queue[UiEvent]" = queue.Queue()

    def post(self, kind: str, **data: Any) -> None:
        self._q.put(UiEvent(kind, data))

    def drain(self) -> list[UiEvent]:
        """Pop all currently pending events (non-blocking)."""
        out: list[UiEvent] = []
        while True:
            try:
                out.append(self._q.get_nowait())
            except queue.Empty:
                return out

    def clear(self) -> int:
        """Discard pending events; returns how many were dropped."""
        dropped = 0
        while True:
            try:
                self._q.get_nowait()
                dropped += 1
            except queue.Empty:
                return dropped

    def pending_count(self) -> int:
        return self._q.qsize()
