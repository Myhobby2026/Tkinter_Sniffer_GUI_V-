"""End-to-end pipeline smoke test (Phase 1 scope):

    SimulatorDevice (worker thread)
        → CaptureManager._on_block (lock-guarded)
        → IntegrityTracker
        → MemoryCaptureStorage

No hardware, no GUI, no file I/O — but the real threading, locking, and
integrity paths are exercised.
"""
import threading
import time

import pytest

from app.core.capture import CaptureConfig, CaptureManager, CaptureState
from app.core.sample_block import unpack_samples
from app.core.storage import MemoryCaptureStorage
from app.errors import CaptureError
from app.hal.simulator import SimulatorDevice


def _make(sim_kwargs=None) -> tuple[SimulatorDevice, CaptureManager, MemoryCaptureStorage]:
    sim = SimulatorDevice(**(sim_kwargs or dict(
        sample_rate_hz=1_000_000, channel_count=4, block_samples=256,
        real_time=False, max_blocks=10,
    )))
    storage = MemoryCaptureStorage()
    storage.create("memory", metadata={"device": "sim"})
    cm = CaptureManager()
    cm.attach(sim, storage)
    return sim, cm, storage


def test_full_capture_cycle():
    sim, cm, storage = _make()
    cm.configure(CaptureConfig(sample_rate_hz=1_000_000, channel_count=4))
    cm.start()
    assert cm.state is CaptureState.RUNNING
    time.sleep(0.15)  # 10 unpaced blocks complete well inside this window
    summary = cm.stop()

    assert summary.block_count == 10
    assert summary.byte_count == 10 * 256  # 4ch → 1 byte/sample
    assert summary.integrity.ok is True
    assert summary.integrity.summary == "OK"

    blocks = list(storage.read_blocks())
    assert [b.seq for b in blocks] == list(range(10))
    assert [b.sample_index for b in blocks] == [i * 256 for i in range(10)]
    assert blocks[-1].is_last
    assert all(b.crc_ok for b in blocks)
    # payload must decode back to the deterministic pattern
    bits = unpack_samples(blocks[0].payload, 4)
    assert bits.shape == (256, 4)
    assert bits[0, 0] == 1 and bits[255, 0] == 1  # CH0 high for first 512 samples


def test_read_blocks_windowing():
    sim, cm, storage = _make()
    cm.configure(CaptureConfig(sample_rate_hz=1_000_000, channel_count=4))
    cm.start()
    time.sleep(0.15)
    cm.stop()
    window = list(storage.read_blocks(start=2, count=3))
    assert [b.seq for b in window] == [2, 3, 4]
    assert len(list(storage.read_blocks(start=9, count=99))) == 1


def test_state_machine_transitions():
    sim, cm, _ = _make()
    with pytest.raises(CaptureError) as excinfo:
        cm.stop()
    assert excinfo.value.code == "CAPTURE_NOT_RUNNING"

    cm.configure(CaptureConfig(sample_rate_hz=1_000_000, channel_count=4))
    cm.start()
    with pytest.raises(CaptureError) as excinfo:
        cm.start()
    assert excinfo.value.code == "CAPTURE_ALREADY_RUNNING"
    with pytest.raises(CaptureError) as excinfo:
        cm.configure(CaptureConfig(sample_rate_hz=1_000_000, channel_count=4))
    assert excinfo.value.code == "CAPTURE_RECONFIG_RUNNING"
    cm.stop()
    # stopped → can start again
    cm.start()
    time.sleep(0.1)
    cm.stop()


def test_attach_refused_while_running():
    sim, cm, storage = _make()
    cm.configure(CaptureConfig(sample_rate_hz=1_000_000, channel_count=4))
    cm.start()
    time.sleep(0.05)
    with pytest.raises(CaptureError) as excinfo:
        cm.attach(sim, MemoryCaptureStorage())
    assert excinfo.value.code == "CAPTURE_ATTACH_RUNNING"
    cm.stop()


class NullDevice(SimulatorDevice):
    """Device that generates no blocks — isolates the manager's ingest path."""

    def _run(self) -> None:  # no worker loop; blocks only via direct _on_block calls
        return None


def test_blocks_from_other_thread_are_thread_safe():
    """Hammer _on_block from 4 threads (future transport worker pattern).

    Verifies lock-guarded counters/storage: no block is lost and no exception
    escapes. (Integrity ordering is a single-stream property, asserted
    elsewhere — interleaved seqs from parallel producers are not a stream.)
    """
    from tests.conftest import make_block

    device = NullDevice(sample_rate_hz=1_000_000, channel_count=4,
                        block_samples=256, real_time=False, max_blocks=0)
    device.connect()
    storage = MemoryCaptureStorage()
    cm = CaptureManager()
    cm.attach(device, storage)
    cm.configure(CaptureConfig(sample_rate_hz=1_000_000, channel_count=4))
    cm.start()

    n_threads, per_thread = 4, 250

    def producer(offset: int) -> None:
        for i in range(per_thread):
            cm._on_block(make_block(seq=offset + i, sample_index=(offset + i) * 8))

    threads = [threading.Thread(target=producer, args=(t * per_thread,)) for t in range(n_threads)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    summary = cm.stop()
    assert summary.block_count == n_threads * per_thread
    assert summary.byte_count == n_threads * per_thread * 8
    assert storage.block_count == n_threads * per_thread


def test_storage_metadata_roundtrip():
    storage = MemoryCaptureStorage()
    storage.create("unused", metadata={"a": 1})
    assert storage.metadata == {"a": 1}
    assert storage.block_count == 0
    assert list(storage.read_blocks()) == []
