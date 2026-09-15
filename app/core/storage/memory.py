"""In-RAM reference storage.

Used by unit/integration tests and as a fallback for the GUI session model.
Deliberately simple — it exists to pin down the CaptureStorage contract and
to exercise the pipeline without file I/O.
"""
from __future__ import annotations

from typing import Any, Iterator

from ..sample_block import CaptureBlock
from .capture_storage import CaptureStorage


class MemoryCaptureStorage(CaptureStorage):
    def __init__(self) -> None:
        self._blocks: list[CaptureBlock] = []
        self._metadata: dict[str, Any] = {}

    @property
    def block_count(self) -> int:
        return len(self._blocks)

    @property
    def metadata(self) -> dict[str, Any]:
        return dict(self._metadata)

    def create(self, path: str | None = None, metadata: dict[str, Any] | None = None) -> None:
        self._blocks = []
        self._metadata = dict(metadata or {})

    def append(self, block: CaptureBlock) -> int:
        self._blocks.append(block)
        return len(self._blocks) - 1

    def read_blocks(self, start: int = 0, count: int | None = None) -> Iterator[CaptureBlock]:
        end = len(self._blocks) if count is None else min(len(self._blocks), start + count)
        for block in self._blocks[start:end]:
            yield block
