"""Capture storage engine interface (spec: Storage Engine, §36).

Contract:
    * append-on-write: captures stream blocks in; readers never wait on a
      writer for data that was already flushed.
    * random read: blocks can be read back by index range (viewport loading,
      replay, export, diff).
    * recoverable: a corrupt region must be *reported* (and skipped by the
      reader with a visible integrity flag), never silently dropped.
    * large-capture safe: implementations must not require the whole capture
      to fit in RAM (the .usn implementation does, Phase 4).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Iterator

from ..sample_block import CaptureBlock


class CaptureStorage(ABC):
    """Append-on-write, random-read store for CaptureBlocks."""

    @property
    @abstractmethod
    def block_count(self) -> int:
        """Number of blocks stored."""

    @property
    @abstractmethod
    def metadata(self) -> dict[str, Any]:
        """Session metadata attached at create() time (device, config, ...)."""

    @property
    def path(self) -> str | None:
        """Backed path, or None for in-memory storages."""
        return None

    @abstractmethod
    def create(self, path: str | Path, metadata: dict[str, Any] | None = None) -> None:
        """Create a new, empty storage at ``path``."""

    @abstractmethod
    def append(self, block: CaptureBlock) -> int:
        """Append one block; returns the block's index in this storage."""

    @abstractmethod
    def read_blocks(self, start: int = 0, count: int | None = None) -> Iterator[CaptureBlock]:
        """Iterate blocks [start, start+count) (count=None → to end)."""

    def flush(self) -> None:
        """Make appended data durable (no-op for in-memory storages)."""

    def close(self) -> None:
        """Release resources (no-op for in-memory storages)."""

    def __enter__(self) -> "CaptureStorage":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()
