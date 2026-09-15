"""Deterministic software simulator of a CaptureDevice.

Two roles:
    * GUI demo: Connect → Simulator, Start, watch blocks + integrity live.
    * Pipeline/decoder tests: ``run_blocks()`` produces deterministic data
      with no timing dependency.

Channel pattern (all 0/1, deterministic for a given configuration):
    CH0  square wave, period 1024 samples  (50% duty)
    CH1  square wave, period 2048 samples  (50% duty)
    CH2  square wave, period 8192 samples  (50% duty)
    CH3  64-bit LCG bit (deterministic PRNG, seed configurable)

``max_sample_rate_hz`` in capabilities is intentionally ``None``: a simulator
has no verified hardware rate, and the application never invents one (§49).
"""
from __future__ import annotations

import threading
import time
from typing import Callable

import numpy as np

from ..core.sample_block import BlockFlags, CaptureBlock, pack_samples
from ..errors import CaptureError, DeviceError
from .capture_device import CaptureConfig, CaptureDevice
from .device import DeviceCapabilities, DeviceInfo, DeviceState

SIMULATOR_DEVICE_ID = "simulator-0001"
MAX_CHANNELS = 4

_INFO = DeviceInfo(
    name="Universal Sniffer Simulator",
    vendor_id="USN",
    product_id="SIM",
    kind="simulator",
    serial_number=SIMULATOR_DEVICE_ID,
)


class SimulatorDevice(CaptureDevice):
    def __init__(
        self,
        sample_rate_hz: int = 1_000_000,
        channel_count: int = MAX_CHANNELS,
        block_samples: int = 4096,
        real_time: bool = True,
        max_blocks: int = 0,
        seed: int = 0xC0FFEE_1234,
    ) -> None:
        super().__init__()
        if not 1 <= channel_count <= MAX_CHANNELS:
            raise CaptureError(
                f"simulator supports 1..{MAX_CHANNELS} channels",
                code="SIM_BAD_CHANNELS",
            )
        self._info = _INFO
        self._rate = int(sample_rate_hz)
        self._nch = int(channel_count)
        self._block_samples = int(block_samples)
        self._real_time = bool(real_time)
        self._max_blocks = int(max_blocks)  # 0 = run until stopped
        self._seed = int(seed) & 0xFFFFFFFFFFFFFFFF
        self._rng = self._seed

        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._active_callback: Callable[[CaptureBlock], None] | None = None
        self._running = False

    # ----------------------------------------------------------------- Device
    @property
    def info(self) -> DeviceInfo:
        return self._info

    def capabilities(self) -> DeviceCapabilities:
        return DeviceCapabilities(
            channel_count=self._nch,
            max_sample_rate_hz=None,  # unknown — never claim
            adc_channels=0,
            supported_protocols=("gpio",),
            supported_triggers=("edge", "level", "pattern"),
            usb_speed="n/a",
            firmware_version="sim-0.1.0",
            hardware_revision="sim-0",
        )

    def connect(self) -> None:
        self._state = DeviceState.CONNECTED

    def disconnect(self) -> None:
        if self._running:
            self.stop_capture()
        self._state = DeviceState.DISCONNECTED

    # -------------------------------------------------------- CaptureDevice
    @property
    def capture_state(self) -> str:
        return "running" if self._running else "idle"

    def configure(self, config: CaptureConfig) -> None:
        if config.channel_count > MAX_CHANNELS:
            raise CaptureError(
                f"simulator supports at most {MAX_CHANNELS} channels",
                code="SIM_BAD_CHANNELS",
            )
        if self._running:
            raise CaptureError("cannot reconfigure while capturing", code="SIM_BUSY")
        self._rate = config.sample_rate_hz
        self._nch = config.channel_count

    def start_capture(self, block_callback: Callable[[CaptureBlock], None]) -> None:
        if self._state is not DeviceState.CONNECTED:
            raise DeviceError("connect the device before capturing", code="SIM_NOT_CONNECTED")
        if self._running:
            raise CaptureError("simulator already capturing", code="SIM_ALREADY_RUNNING")
        self._active_callback = block_callback
        self._stop.clear()
        self._running = True
        self._thread = threading.Thread(
            target=self._run, name="simulator-capture", daemon=True
        )
        self._thread.start()

    def stop_capture(self) -> None:
        if not self._running:
            return
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=5.0)
        self._running = False
        self._thread = None

    # ------------------------------------------------------------- internals
    def _run(self) -> None:
        emitted = 0
        callback = self._active_callback
        assert callback is not None
        while not self._stop.is_set():
            ending = self._max_blocks > 0 and emitted >= self._max_blocks - 1
            block = self._make_block(emitted, ending)
            emitted += 1
            callback(block)
            if ending:
                break
            if self._real_time:
                time.sleep(self._block_samples / self._rate)

    def _make_block(self, seq: int, ending: bool) -> CaptureBlock:
        bits = self._make_samples(self._block_samples)
        flags = BlockFlags.LAST_BLOCK if ending else BlockFlags.NONE
        return CaptureBlock(
            seq=seq,
            sample_index=seq * self._block_samples,
            device_ts_us=int(time.monotonic() * 1_000_000),
            channel_mask=(1 << self._nch) - 1,
            sample_count=self._block_samples,
            payload=pack_samples(bits, self._nch),
            flags=flags,
        )

    def run_blocks(self, n: int, callback: Callable[[CaptureBlock], None] | None = None) -> None:
        """Synchronous deterministic generation — test helper (no thread, no sleep).

        Uses the active capture callback when ``callback`` is not given.
        """
        cb = callback if callback is not None else self._active_callback
        if cb is None:
            raise CaptureError("no block callback available", code="SIM_NO_CALLBACK")
        for i in range(n):
            cb(self._make_block(i, i == n - 1))

    def _make_samples(self, n: int) -> np.ndarray:
        """Deterministic sample pattern; identical for identical configuration."""
        out = np.empty((n, self._nch), dtype=np.uint8)
        for i in range(n):
            out[i, 0] = 1 if i % 1024 < 512 else 0
            if self._nch > 1:
                out[i, 1] = 1 if i % 2048 < 1024 else 0
            if self._nch > 2:
                out[i, 2] = 1 if i % 8192 < 4096 else 0
            if self._nch > 3:
                self._rng = (
                    self._rng * 6364136223846793005 + 1442695040888963407
                ) & 0xFFFFFFFFFFFFFFFF
                out[i, 3] = (self._rng >> 31) & 1
        return out
