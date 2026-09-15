"""Capture integrity (spec §12): NO silent data loss.

Detects and counts:
    * sequence gaps  (missing blocks)
    * duplicate / late blocks
    * CRC failures
    * device buffer overflows (block flags)

The GUI must display the :class:`IntegrityReport.summary` — either ``OK`` or
``WARNING: ...`` — it must never present a lossy capture as clean.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from .sample_block import CaptureBlock


def _plural(n: int, singular: str, plural: str | None = None, suffix: str = "") -> str:
    """'1 block missing' / '37 blocks missing' style counting."""
    word = singular if n == 1 else (plural or singular + "s")
    return f"{n} {word}" + (f" {suffix}" if suffix else "")


@dataclass
class IntegrityReport:
    """Snapshot of capture integrity state."""

    blocks_received: int = 0
    missing_blocks: int = 0
    duplicate_blocks: int = 0
    crc_errors: int = 0
    overflow_blocks: int = 0
    last_seq: int = -1

    @property
    def ok(self) -> bool:
        return (
            self.missing_blocks == 0
            and self.crc_errors == 0
            and self.overflow_blocks == 0
            and self.duplicate_blocks == 0
        )

    @property
    def summary(self) -> str:
        """Display string (spec §12), e.g. 'OK' or
        'WARNING: 37 blocks missing, 2 CRC errors, 1 buffer overflow'."""
        if self.ok:
            return "OK"
        parts: list[str] = []
        if self.missing_blocks:
            parts.append(_plural(self.missing_blocks, "block", suffix="missing"))
        if self.crc_errors:
            parts.append(_plural(self.crc_errors, "CRC error"))
        if self.overflow_blocks:
            parts.append(_plural(self.overflow_blocks, "buffer overflow"))
        if self.duplicate_blocks:
            parts.append(_plural(self.duplicate_blocks, "duplicate block"))
        return "WARNING: " + ", ".join(parts)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "summary": self.summary,
            "blocks_received": self.blocks_received,
            "missing_blocks": self.missing_blocks,
            "duplicate_blocks": self.duplicate_blocks,
            "crc_errors": self.crc_errors,
            "overflow_blocks": self.overflow_blocks,
            "last_seq": self.last_seq,
        }


class IntegrityTracker:
    """Feeds blocks as they arrive; maintains gap/CRC/overflow accounting."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self._received = 0
        self._missing = 0
        self._duplicate = 0
        self._crc = 0
        self._overflow = 0
        self._last_seq = -1
        self._expected = 0

    def feed(self, block: CaptureBlock) -> None:
        """Account for one received block. Caller must serialise if multithreaded."""
        self._received += 1
        seq = block.seq
        if seq == self._expected:
            self._expected += 1
        elif seq > self._expected:
            self._missing += seq - self._expected
            self._expected = seq + 1
        else:  # late or duplicated sequence number
            self._duplicate += 1
        if not block.crc_ok:
            self._crc += 1
        if block.has_overflow:
            self._overflow += 1
        self._last_seq = max(self._last_seq, seq)

    def report(self) -> IntegrityReport:
        return IntegrityReport(
            blocks_received=self._received,
            missing_blocks=self._missing,
            duplicate_blocks=self._duplicate,
            crc_errors=self._crc,
            overflow_blocks=self._overflow,
            last_seq=self._last_seq,
        )
