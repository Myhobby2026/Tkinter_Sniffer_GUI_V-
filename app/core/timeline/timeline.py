"""Master timeline (spec §13).

One master timeline per capture session. Internally everything is integer
sample units; floating point appears only at the display edge.

    t_seconds(sample_index) = (sample_index - start_index) / sample_rate
    t_utc_ns(sample_index)   = epoch_utc_ns + (sample_index - start_index) * 1e9 // sample_rate

All decoded protocol events, trigger positions, cursors, bookmarks and
measurements map onto this timeline via integer sample indices.
"""
from __future__ import annotations

from ...errors import CaptureError


class Timeline:
    """Integer-unit master timeline for one capture session."""

    def __init__(
        self,
        sample_rate_hz: int,
        epoch_utc_ns: int = 0,
        start_index: int = 0,
    ) -> None:
        rate = int(sample_rate_hz)
        if rate <= 0:
            raise CaptureError(
                "sample_rate_hz must be a positive integer", code="TIMELINE_BAD_RATE"
            )
        self._rate = rate
        self._epoch = int(epoch_utc_ns)
        self._start = int(start_index)

    @property
    def sample_rate_hz(self) -> int:
        return self._rate

    @property
    def epoch_utc_ns(self) -> int:
        """Wall-clock anchor (UTC nanoseconds) of sample ``start_index``."""
        return self._epoch

    @property
    def start_index(self) -> int:
        return self._start

    def index_to_seconds(self, index: int) -> float:
        """Relative time in seconds (float; display/measure edge only)."""
        return (index - self._start) / self._rate

    def seconds_to_index(self, seconds: float) -> int:
        """Nearest sample index for a relative time in seconds."""
        return self._start + int(round(seconds * self._rate))

    def index_to_utc_ns(self, index: int) -> int:
        """Exact integer UTC nanoseconds on the master timeline.

        Integer division (floor). Exact when ``sample_rate`` divides 1e9
        (e.g. 1 MHz, 10 MHz, 25 MHz); sub-nanosecond floor error otherwise.
        """
        delta = index - self._start
        if delta < 0:
            raise CaptureError(
                "index precedes timeline start", code="TIMELINE_BAD_INDEX"
            )
        return self._epoch + delta * 1_000_000_000 // self._rate

    def describe(self) -> dict:
        return {
            "sample_rate_hz": self._rate,
            "epoch_utc_ns": self._epoch,
            "start_index": self._start,
        }
