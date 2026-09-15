"""USB transport — implemented in Phase 3 (see docs/capture_protocol.md).

The stub exists so the module layout is stable and accidental use fails fast
with an actionable error instead of an ImportError at runtime.
"""
from __future__ import annotations

from typing import Any

from ..errors import USBError
from .transport import Transport


class USBTransport(Transport):
    """USB CDC/HS transport for the Teensy 4.1 bridge (Phase 3).

    Will provide: framing, sequence validation, CRC-32, disconnect detection,
    reconnect with resume, throughput monitoring (spec §10/§11).
    """

    def __init__(self, name: str = "usb") -> None:
        super().__init__(name)

    def open(self, options: dict[str, Any] | None = None) -> None:
        raise USBError(
            "USB transport is implemented in Phase 3", code="USB_NOT_IMPLEMENTED"
        )

    def close(self) -> None:
        raise USBError(
            "USB transport is implemented in Phase 3", code="USB_NOT_IMPLEMENTED"
        )

    def send_command(self, command: bytes) -> None:
        raise USBError(
            "USB transport is implemented in Phase 3", code="USB_NOT_IMPLEMENTED"
        )
