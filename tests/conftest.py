"""Shared pytest fixtures/helpers (pure Python — no hardware, no display)."""
from __future__ import annotations

import sys
from pathlib import Path

# Ensure the repo root is importable when running pytest from anywhere.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402

from app.core.sample_block import CaptureBlock, SampleBatch  # noqa: E402


def make_batch(
    sample_rate_hz: int = 1_000_000,
    start_index: int = 0,
    n_samples: int = 64,
    n_channels: int = 4,
    pattern: str = "square0",
    block_seq: int = 0,
) -> SampleBatch:
    """Deterministic synthetic batch for decoder/pipeline tests."""
    bits = np.zeros((n_samples, n_channels), dtype=np.uint8)
    for i in range(n_samples):
        if pattern == "square0":
            bits[i, 0] = 1 if i % 16 < 8 else 0
        elif pattern == "all_high":
            bits[i, :] = 1
        elif pattern == "static":
            bits[i, :] = 0
        else:
            raise ValueError(f"unknown pattern {pattern!r}")
    return SampleBatch(
        sample_rate_hz=sample_rate_hz,
        start_index=start_index,
        samples=bits,
        channel_mask=(1 << n_channels) - 1,
        block_seq=block_seq,
    )


def make_block(
    seq: int = 0,
    sample_index: int = 0,
    n_samples: int = 8,
    n_channels: int = 4,
    crc_ok: bool = True,
    overflow: bool = False,
    payload: bytes | None = None,
) -> CaptureBlock:
    """Small deterministic block; payload defaults to all-zero samples."""
    flags = 1 if overflow else 0  # BlockFlags.OVERFLOW
    if payload is None:
        payload = b"\x00" * n_samples
    return CaptureBlock(
        seq=seq,
        sample_index=sample_index,
        device_ts_us=seq * 1000,
        channel_mask=(1 << n_channels) - 1,
        sample_count=n_samples,
        payload=payload,
        flags=flags,
        crc_ok=crc_ok,
    )
