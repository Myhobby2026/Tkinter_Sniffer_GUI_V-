import numpy as np
import pytest

from app.core.sample_block import (
    BlockFlags,
    CaptureBlock,
    SampleBatch,
    pack_samples,
    sample_width,
    unpack_samples,
)
from app.errors import CaptureError


def test_sample_width():
    assert sample_width(1) == 1
    assert sample_width(8) == 1
    assert sample_width(9) == 2
    assert sample_width(16) == 2
    with pytest.raises(CaptureError):
        sample_width(0)
    with pytest.raises(CaptureError):
        sample_width(17)


def test_pack_unpack_roundtrip_4ch():
    bits = (np.arange(32 * 4).reshape(32, 4) % 2).astype(np.uint8)
    payload = pack_samples(bits, 4)
    assert len(payload) == 32  # 1 byte/sample for <= 8 channels
    assert unpack_samples(payload, 4).tolist() == bits.tolist()


def test_pack_unpack_roundtrip_16ch():
    rng = np.random.default_rng(1234)
    bits = rng.integers(0, 2, size=(200, 16), dtype=np.uint8)
    payload = pack_samples(bits, 16)
    assert len(payload) == 200 * 2  # 2 bytes/sample
    assert unpack_samples(payload, 16).tolist() == bits.tolist()


def test_channel_bit_order():
    # channel 0 must be the least-significant bit
    bits = np.zeros((1, 4), dtype=np.uint8)
    bits[0, 3] = 1
    payload = pack_samples(bits, 4)
    assert payload == b"\x08"
    bits[0, 0] = 1
    assert pack_samples(bits, 4) == b"\x09"


def test_bad_shape_rejected():
    with pytest.raises(CaptureError) as excinfo:
        pack_samples(np.zeros((4, 3), dtype=np.uint8), 4)
    assert excinfo.value.code == "BLOCK_BAD_SHAPE"


def test_bad_payload_length_rejected():
    # 9 channels → 2 bytes/sample; 3 bytes is not a multiple of 2
    with pytest.raises(CaptureError) as excinfo:
        unpack_samples(b"\x00\x00\x01", 9)
    assert excinfo.value.code == "BLOCK_BAD_PAYLOAD"


def test_block_field_validation():
    with pytest.raises(CaptureError) as excinfo:
        CaptureBlock(seq=-1, sample_index=0, device_ts_us=0, channel_mask=0xF,
                     sample_count=1, payload=b"\x00")
    assert excinfo.value.code == "BLOCK_BAD_FIELD"
    with pytest.raises(CaptureError):
        CaptureBlock(seq=0, sample_index=0, device_ts_us=0, channel_mask=0,
                     sample_count=1, payload=b"\x00")


def test_block_flags_and_properties():
    block = CaptureBlock(seq=0, sample_index=0, device_ts_us=0, channel_mask=0xF,
                         sample_count=4, payload=b"\x00" * 4,
                         flags=BlockFlags.OVERFLOW | BlockFlags.LAST_BLOCK)
    assert block.has_overflow
    assert block.is_last
    assert block.nbytes == 4


def test_batch_properties():
    batch = SampleBatch(sample_rate_hz=1_000_000, start_index=100,
                        samples=np.zeros((10, 4), dtype=np.uint8))
    assert batch.n_samples == 10
    assert batch.n_channels == 4
    assert batch.end_index == 110
    assert batch.duration_seconds == pytest.approx(1e-5)


def test_batch_to_dict_has_no_raw_data():
    batch = SampleBatch(sample_rate_hz=1000, start_index=0,
                        samples=np.ones((5, 2), dtype=np.uint8))
    d = batch.to_dict()
    assert "samples" not in d
    assert d["n_samples"] == 5
