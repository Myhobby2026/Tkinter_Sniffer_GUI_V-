"""Capture data model (spec §10/§11, host side).

CaptureBlock is the atomic unit flowing from the transport through integrity
and into storage. SampleBatch is the decoded view decoders consume.

Packing (little-endian, host and device agree):
    * channel c occupies bit c of each sample row (LSB = channel 0)
    * 16 channels pack to one uint16 per sample (2 bytes)
    * <= 8 channels pack to one uint8 per sample (1 byte)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntFlag
from typing import Any

import numpy as np

from ..errors import CaptureError


class BlockFlags(IntFlag):
    NONE = 0
    OVERFLOW = 1 << 0      # device ring/DMA overflow during this block
    TRIGGER_FIRED = 1 << 1  # trigger condition matched inside this block
    LAST_BLOCK = 1 << 2     # final block of the capture
    RATE_CHANGE = 1 << 3    # sample rate changed after this block
    TRUNCATED = 1 << 4      # payload truncated by device (must be flagged, never silent)


def _check_nonneg(name: str, value: int) -> None:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise CaptureError(
            f"CaptureBlock.{name} must be a non-negative integer",
            code="BLOCK_BAD_FIELD",
            context={"field": name},
        )


@dataclass(frozen=True)
class CaptureBlock:
    """One captured block: contiguous samples for the configured channels.

    Immutable and hashable — safe to share between threads.
    """

    seq: int                 # 32-bit sequence number (device-ordered)
    sample_index: int        # 64-bit absolute sample index on the master timeline
    device_ts_us: int        # device timestamp counter (32-bit us + host wrap tracking)
    channel_mask: int        # 16-bit mask of channels present in the payload
    sample_count: int        # samples in this block
    payload: bytes           # packed samples, little-endian
    flags: BlockFlags = BlockFlags.NONE
    crc_ok: bool = True      # CRC verified by the transport layer

    def __post_init__(self) -> None:
        object.__setattr__(self, "flags", BlockFlags(self.flags))
        _check_nonneg("seq", self.seq)
        _check_nonneg("sample_index", self.sample_index)
        _check_nonneg("sample_count", self.sample_count)
        if not 0 < self.channel_mask <= 0xFFFF:
            raise CaptureError(
                "channel_mask must be within 0x0001..0xFFFF", code="BLOCK_BAD_MASK"
            )

    @property
    def nbytes(self) -> int:
        return len(self.payload)

    @property
    def is_last(self) -> bool:
        return bool(self.flags & BlockFlags.LAST_BLOCK)

    @property
    def has_overflow(self) -> bool:
        return bool(self.flags & BlockFlags.OVERFLOW)

    def to_dict(self) -> dict[str, Any]:
        """Metadata view (never embeds the payload)."""
        return {
            "seq": self.seq,
            "sample_index": self.sample_index,
            "device_ts_us": self.device_ts_us,
            "channel_mask": self.channel_mask,
            "sample_count": self.sample_count,
            "payload_bytes": len(self.payload),
            "flags": int(self.flags),
            "crc_ok": self.crc_ok,
        }


def sample_width(n_channels: int) -> int:
    """Bytes per packed sample for ``n_channels`` channels."""
    if not 1 <= n_channels <= 16:
        raise CaptureError(
            "channel count must be 1..16", code="BLOCK_BAD_CHANNELS"
        )
    return 1 if n_channels <= 8 else 2


def pack_samples(bits: np.ndarray, n_channels: int) -> bytes:
    """Pack an (n, n_channels) array of 0/1 values into little-endian rows.

    Channel c is bit c (LSB = channel 0). Vectorised per channel; the channel
    loop (max 16) is cheap compared to the array size.
    """
    bits = np.ascontiguousarray(bits)
    if bits.ndim != 2 or bits.shape[1] != n_channels:
        raise CaptureError(
            "bits must have shape (n, n_channels)", code="BLOCK_BAD_SHAPE"
        )
    dtype = np.uint8 if sample_width(n_channels) == 1 else np.uint16
    rows = np.zeros(bits.shape[0], dtype=dtype)
    for c in range(n_channels):
        rows |= bits[:, c].astype(dtype) << c
    return rows.tobytes(order="C")


def unpack_samples(payload: bytes, n_channels: int) -> np.ndarray:
    """Inverse of :func:`pack_samples` → (n, n_channels) uint8 array of 0/1."""
    width = sample_width(n_channels)
    if len(payload) % width != 0:
        raise CaptureError(
            "payload length is not a multiple of the sample width",
            code="BLOCK_BAD_PAYLOAD",
        )
    dtype = np.uint8 if width == 1 else np.uint16
    raw = np.frombuffer(payload, dtype=dtype)
    out = np.empty((raw.size, n_channels), dtype=np.uint8)
    for c in range(n_channels):
        out[:, c] = ((raw >> c) & 1).astype(np.uint8)
    return out


@dataclass
class SampleBatch:
    """A window of decoded samples on the master timeline.

    This is the unit decoders consume (spec §16/§17). It carries only sample
    data plus timeline context — no GUI references, no transport references.
    """

    sample_rate_hz: int
    start_index: int
    samples: np.ndarray  # (n, n_channels) uint8, values 0/1
    channel_mask: int = 0
    block_seq: int = 0

    def __post_init__(self) -> None:
        self.samples = np.ascontiguousarray(self.samples, dtype=np.uint8)

    @property
    def n_samples(self) -> int:
        return int(self.samples.shape[0])

    @property
    def n_channels(self) -> int:
        return int(self.samples.shape[1])

    @property
    def end_index(self) -> int:
        return self.start_index + self.n_samples

    @property
    def duration_seconds(self) -> float:
        return self.n_samples / self.sample_rate_hz

    def to_dict(self) -> dict[str, Any]:
        """Summary only — never serialise raw sample arrays."""
        return {
            "sample_rate_hz": self.sample_rate_hz,
            "start_index": self.start_index,
            "n_samples": self.n_samples,
            "n_channels": self.n_channels,
            "channel_mask": self.channel_mask,
            "block_seq": self.block_seq,
        }
