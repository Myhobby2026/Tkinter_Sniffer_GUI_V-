import pytest

from app.errors import CaptureError, DeviceError
from app.hal.device import DeviceState
from app.hal.simulator import MAX_CHANNELS, SIMULATOR_DEVICE_ID, SimulatorDevice


def test_capabilities_never_claim_unmeasured_rate():
    sim = SimulatorDevice()
    caps = sim.capabilities()
    assert caps.max_sample_rate_hz is None  # unknown — must not guess
    assert caps.channel_count == 4
    assert caps.firmware_version == "sim-0.1.0"
    assert "gpio" in caps.supported_protocols


def test_connect_disconnect():
    sim = SimulatorDevice()
    assert sim.state is DeviceState.DISCONNECTED
    sim.connect()
    assert sim.state is DeviceState.CONNECTED
    assert sim.health()["ok"] is True
    sim.disconnect()
    assert sim.state is DeviceState.DISCONNECTED


def test_start_requires_connect():
    sim = SimulatorDevice(real_time=False, max_blocks=1)
    with pytest.raises(DeviceError) as excinfo:
        sim.start_capture(lambda b: None)
    assert excinfo.value.code == "SIM_NOT_CONNECTED"


def test_configure_limits():
    sim = SimulatorDevice()
    sim.connect()
    with pytest.raises(CaptureError):
        from app.hal.capture_device import CaptureConfig

        sim.configure(CaptureConfig(sample_rate_hz=1000, channel_count=MAX_CHANNELS + 1))


def test_run_blocks_deterministic():
    collected_a, collected_b = [], []
    SimulatorDevice(sample_rate_hz=1_000_000, channel_count=4, block_samples=64,
                    seed=42).run_blocks(3, collected_a.append)
    SimulatorDevice(sample_rate_hz=1_000_000, channel_count=4, block_samples=64,
                    seed=42).run_blocks(3, collected_b.append)
    assert [b.payload for b in collected_a] == [b.payload for b in collected_b]
    assert [b.seq for b in collected_a] == [0, 1, 2]
    assert [b.sample_index for b in collected_a] == [0, 64, 128]
    assert collected_a[-1].is_last
    assert not collected_a[0].is_last


def test_run_blocks_pattern_known():
    from app.core.sample_block import unpack_samples

    collected = []
    SimulatorDevice(sample_rate_hz=1_000_000, channel_count=4, block_samples=1024,
                    seed=1).run_blocks(1, collected.append)
    bits = unpack_samples(collected[0].payload, 4)
    # CH0: 512 high, 512 low
    assert bits[0, 0] == 1
    assert bits[511, 0] == 1
    assert bits[512, 0] == 0
    # CH1: period 2048 → high across the whole 1024-sample block
    assert (bits[:, 1] == 1).all()


def test_threaded_capture_and_stop():
    import time

    sim = SimulatorDevice(sample_rate_hz=1_000_000, channel_count=2,
                          block_samples=128, real_time=False, max_blocks=0)
    sim.connect()
    collected = []
    sim.start_capture(collected.append)
    assert sim.capture_state == "running"
    time.sleep(0.05)
    sim.stop_capture()
    assert sim.capture_state == "idle"
    assert len(collected) >= 1
    seqs = [b.seq for b in collected]
    assert seqs == list(range(len(seqs)))  # no gaps
    # stopping twice is safe
    sim.stop_capture()
