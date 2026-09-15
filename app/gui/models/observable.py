"""Minimal thread-safe observable base for GUI models (no Tkinter)."""
from __future__ import annotations

import threading
from typing import Callable


class Observable:
    """Listeners are called with no arguments and must be fast.

    The GUI thread normally reads models directly in its poll loop; listeners
    exist for future push-based updates from worker threads.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._listeners: list[Callable[[], None]] = []

    def subscribe(self, callback: Callable[[], None]) -> None:
        with self._lock:
            self._listeners.append(callback)

    def unsubscribe(self, callback: Callable[[], None]) -> None:
        with self._lock:
            if callback in self._listeners:
                self._listeners.remove(callback)

    def _notify_locked(self) -> None:
        """Call with the lock held; listeners run outside the lock."""
        listeners = list(self._listeners)
        for callback in listeners:
            callback()
