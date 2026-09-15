import pytest

from app.core.timeline import Timeline
from app.errors import CaptureError


def test_seconds_roundtrip():
    t = Timeline(sample_rate_hz=1_000_000)
    assert t.index_to_seconds(2_500_000) == 2.5
    assert t.seconds_to_index(2.5) == 2_500_000


def test_epoch_ns_is_integer_and_exact():
    # 3 samples at 1 MS/s = 3 us = 3000 ns (1 us = 1000 ns)
    t = Timeline(sample_rate_hz=1_000_000, epoch_utc_ns=1_000)
    assert t.index_to_utc_ns(3) == 1_000 + 3 * 1_000


def test_start_offset():
    t = Timeline(sample_rate_hz=100, start_index=1000)
    assert t.index_to_seconds(1010) == 0.1
    assert t.seconds_to_index(0.0) == 1000


def test_describe():
    t = Timeline(sample_rate_hz=10_000_000, epoch_utc_ns=7, start_index=1)
    assert t.describe() == {"sample_rate_hz": 10_000_000, "epoch_utc_ns": 7, "start_index": 1}


def test_invalid_rate():
    with pytest.raises(CaptureError) as excinfo:
        Timeline(sample_rate_hz=0)
    assert excinfo.value.code == "TIMELINE_BAD_RATE"


def test_index_before_start_rejected():
    t = Timeline(sample_rate_hz=1_000_000, start_index=10)
    with pytest.raises(CaptureError) as excinfo:
        t.index_to_utc_ns(5)
    assert excinfo.value.code == "TIMELINE_BAD_INDEX"
