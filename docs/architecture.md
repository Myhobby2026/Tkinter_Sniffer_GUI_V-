# Universal Sniffer — Architecture Review

Status: **approved baseline** (Phase 1 implemented on top of this document).
Any change to a stable interface requires the change-control report from
spec §54: *Current Architecture → Problem → Proposed Change → Benefits →
Risks → Compatibility Impact → Testing Plan*.

---

## 1. Complete architecture

Six layers, strict downward dependencies:

```
┌─────────────────────────────────────────────────────────────────────┐
│ L6  GUI  (app/gui)                                                  │
│     Tkinter/ttk views + panels · pure-Python controllers/models     │
│     Views never contain logic; workers never touch widgets          │
├─────────────────────────────────────────────────────────────────────┤
│ L5  Application  (app/main.py, gui/models, gui/ui_queue)            │
│     Object graph wiring · sessions · commands · UI event pump       │
├─────────────────────────────────────────────────────────────────────┤
│ L4  Core engine  (app/core)                                         │
│     capture manager · timeline · integrity · storage · (Phase 12:   │
│     analysis, measurements, search) · (Phase 4: replay)             │
├─────────────────────────────────────────────────────────────────────┤
│ L3  Protocol decoders  (app/protocol)                               │
│     API + registry now · SPI/I2C/UART Phase 7-9 · CAN/LIN Phase 10  │
├─────────────────────────────────────────────────────────────────────┤
│ L2  Transport  (app/transport)                                      │
│     USB CDC/HS Phase 3 · framing, CRC, seq validation, reconnect    │
├─────────────────────────────────────────────────────────────────────┤
│ L1  HAL  (app/hal)                                                  │
│     Device / CaptureDevice / DeviceCapabilities / DeviceManager     │
│     + deterministic SimulatorDevice (no Teensy assumptions)         │
├─────────────────────────────────────────────────────────────────────┤
│ L0  Hardware  (firmware/teensy41)                                   │
│     Teensy 4.1 · future: STM32 / RP2040 / FPGA / Ethernet device    │
└─────────────────────────────────────────────────────────────────────┘
```

**Dependency rules**

1. A layer may import only *lower* layers (L6 → L5 → L4 → L3 → L2 → L1).
2. **Shared-kernel exception:** pure data/logic modules with no behaviour —
   `app.errors`, `app.logging_setup`, `app.config`, `app.core.timeline`,
   `app.core.sample_block`, `app.core.integrity` — may be imported by any
   layer. This is how the HAL and transport describe blocks without depending
   on the core engine.
3. Tkinter imports exist ONLY in `app/gui/main_window.py`, `app/gui/theme.py`,
   `app/gui/panels/*`. Everything else in `app/gui` is pure Python and is
   unit-tested headless.
4. Decoders never import the GUI; decoders consume `SampleBatch` and emit
   `DecodedEvent` (spec §7 "GOOD" example, enforced by code review + imports).

## 2. Repository structure

```
UniversalSniffer/
├── README.md  LICENSE  requirements.txt  requirements-dev.txt  pyproject.toml
├── config/                 default.json (bundled defaults)
├── docs/                   architecture.md (this file) · development.md
│                           capture_protocol.md · file_format.md
│                           decoder_api.md · trigger_engine.md · performance.md
├── app/
│   ├── main.py             entry point + Application object graph
│   ├── errors.py           structured error model (§45)
│   ├── config.py           validated configuration
│   ├── logging_setup.py    TRACE..CRITICAL, usn.* loggers, export (§46)
│   ├── session.py          CaptureSession model (§35)
│   ├── core/               capture/ timeline/ storage/ integrity · analysis,
│   │                       measurements, search, replay (later phases)
│   ├── transport/          transport.py (ABC) · usb_transport.py (Phase 3)
│   │                       transport_manager.py
│   ├── hal/                device.py · capture_device.py · device_manager.py
│   │                       simulator.py
│   ├── protocol/           decoder_api.py · decoder_registry.py
│   ├── trigger/            trigger_api.py (model + interfaces)
│   ├── waveform/ hex/ scripting/ plugins/ export/ diagnostics/
│   └── gui/                main_window.py · theme.py · ui_queue.py ·
│                           commands.py · models/ · controllers/ ·
│                           panels/ · views/ · dialogs/ · widgets/
├── firmware/teensy41/      (Phase 2+) src/ hal/ capture/ dma/ usb/ trigger/
├── tests/                  unit/ integration/ protocol/ performance/ gui/
└── tools/                  (Phase 16+) signal_generator/ capture_converter/
```

## 3. Module responsibilities (Phase 1 scope in bold)

| Module | Responsibility | Must NOT do |
|---|---|---|
| **app.main** | Wire object graph; entry point | Contain logic; import Tk at module top |
| **app.errors** | 12 structured error categories | Log or print |
| **app.config** | Load/merge/validate config | Side effects beyond reading files |
| **app.logging_setup** | usn.* loggers, TRACE, export | Format application data |
| **app.core.timeline** | Integer master timeline | Floats as storage; I/O |
| **app.core.sample_block** | CaptureBlock, pack/unpack, SampleBatch | Device assumptions |
| **app.core.integrity** | Gap/CRC/overflow accounting | Reporting (display) |
| **app.core.storage** | Block store ABC + memory impl | Decoding; GUI |
| **app.core.capture** | Device+storage+integrity orchestration, state machine | Threading UI; decode |
| **app.hal** | Device identity/capabilities/lifecycle | Protocol logic |
| **app.hal.simulator** | Deterministic test/demo capture source | Claim measured rates |
| **app.transport** | Link events, command outbox, registry | Frame parsing details (impl.) |
| **app.protocol** | Decoder API/registry/event model | Tkinter; raw channel numbers |
| **app.trigger** | Trigger spec model + engine interfaces | Evaluation (Phase 11) |
| **app.session** | Session metadata model | Persistence (Phase 4) |
| **app.gui.controllers** | Command → application actions | Tkinter imports |
| **app.gui.models** | Observable status snapshots | Tkinter imports |
| **app.gui.ui_queue** | Thread-safe worker→GUI channel | Widget access |
| **app.gui.main_window/panels/theme** | Widgets, layout, menus, status bar | Business logic in callbacks |

## 4. Python interface proposal (final in Phase 1)

```python
# app/hal/device.py
class Device(ABC):
    info: DeviceInfo                      # name, vendor, product, kind, serial
    state: DeviceState                    # DISCONNECTED/CONNECTING/CONNECTED/FAULT
    def capabilities(self) -> DeviceCapabilities   # live query (§15)
    def connect(self) / disconnect(self) / health(self)

@dataclass DeviceCapabilities:            # GUI enables features from HERE only
    channel_count; max_sample_rate_hz: int | None   # None = unknown, never guess
    adc_channels; supported_protocols; supported_triggers
    usb_speed; firmware_version; hardware_revision

# app/hal/capture_device.py
class CaptureDevice(Device):
    def configure(self, config: CaptureConfig) -> None
    def start_capture(self, block_callback: Callable[[CaptureBlock], None]) -> None
    def stop_capture(self) -> None        # no callbacks after return
    @property capture_state -> str

# app/transport/transport.py
class Transport(ABC):
    state: TransportState                 # CLOSED/OPEN/DEGRADED/FAULT
    def open(options) / close() / send_command(bytes)  # bounded, backpressure
    def post_event(TransportEvent) / drain_events(max) -> list   # non-blocking

# app/core/sample_block.py
@dataclass(frozen=True) CaptureBlock:     # immutable, hashable, thread-shareable
    seq: int; sample_index: int; device_ts_us: int; channel_mask: int
    sample_count: int; payload: bytes; flags: BlockFlags; crc_ok: bool
class SampleBatch:                        # decoder input (numpy uint8 (n, nch))
    sample_rate_hz; start_index; samples; channel_mask; block_seq

# app/core/storage/capture_storage.py
class CaptureStorage(ABC):
    block_count; metadata; path
    def create(path, metadata) / append(block) -> int
    def read_blocks(start, count) -> Iterator[CaptureBlock]
    def flush() / close()                 # context manager

# app/core/capture/capture_manager.py
class CaptureManager:
    state: CaptureState                   # IDLE/RUNNING/STOPPED/ERROR
    attach(device, storage) / configure(CaptureConfig)
    start() / stop() -> CaptureSummary    # thread-safe _on_block
    integrity_report / live_stats()

# app/protocol/decoder_api.py  (see docs/decoder_api.md)
class ProtocolDecoder(ABC):
    info -> DecoderInfo                   # id, api_version, required channels
    configure(dict) / reset()
    process(SampleBatch) -> list[DecodedEvent]
    flush() -> list[DecodedEvent]
@dataclass DecodedEvent: protocol, event_type, start_index, duration,
    channel, fields, payload, text, status(OK/WARNING/ERROR), errors

# app/trigger/trigger_api.py  (see docs/trigger_engine.md)
@dataclass TriggerCondition / TriggerSpec  # JSON-serializable
class TriggerEngine:  compile(spec) -> CompiledTrigger; validate(spec)
class CompiledTrigger: process(batch) -> TriggerResult | None; reset()
```

## 5. Tkinter GUI architecture

Pattern: **Views (widgets) ⇄ Commands ⇄ Controllers (pure logic) ⇄ Models
(observables) ⇄ UiEvents ⇄ Views**. No other path exists between the GUI and
the engine.

```
Menu/toolbar button ──Command──▶ MainController.execute()   (GUI thread, fast)
                                     │  mutates app-layer state
                                     ▼
                    DeviceModel / CaptureModel (thread-safe snapshots)
                    UiEventQueue (queue.Queue, thread-safe)
                                     │
Workers ──UiEvent──▶ UiEventQueue ◀──
                                     │
                    root.after(50 ms) poll loop (GUI thread)
                                     ▼
                    status bar / tree / panel updates  ← only widget mutation
```

- **Commands** (`app/gui/commands.py`): `Command(name, args)`; the callback is
  `lambda: self._on_command(Command(Cmd.CAPTURE_START))` — nothing else.
- **Controller** (`app/gui/controllers/main_controller.py`): routing table
  name → handler; every handler returns `CommandResult(ok, message, data)`;
  all exceptions are caught and converted to structured results (a bad
  command can never crash the GUI thread).
- **Views** (`main_window.py`, `panels/`): build widgets, bind commands,
  refresh from models in `_poll`. Theme: two ttk 'clam' palettes (dark/light).
- **Panels**: `PanelSpec(id, title, build)` registered with `PanelManager`;
  Phase 1 layout: left devices / center waveform / bottom transactions /
  right inspector, in nested `ttk.PanedWindow`s. A docking library can
  replace `build_layout()` without touching the engine (spec §41).
- Status bar always shows: `Device: … · Capture: … · Capture Integrity: OK|WARNING: …`
  (integrity string comes from `IntegrityReport.summary`, spec §12).

## 6. Thread/process model

Phase 1 (implemented):

```
GUI thread                    simulator worker thread
   │  MainWindow._poll after(50)      │  blocks (lock-guarded _on_block)
   │  command execute (fast)          ▼
   ▼                        CaptureManager ──▶ IntegrityTracker ──▶ Storage
UiEventQueue ◀──post──────────────────────────────┘
```

Planned (Phases 2-4, same rules):

```
Tkinter thread  ◀──after(50)── UiEventQueue ◀──post──┐
      │                                               │
      ▼ Command                                       │
MainController ──▶ CaptureManager ──▶ Storage (single writer thread,
                                        bounded queue, backpressure:
                                        pause ingest — never drop)
DeviceWorker thread: Transport.open/read loop
      │ post(TransportEvent BLOCK) ──▶ IngestQueue (bounded)
IngestWorker: validate CRC/seq (transport did CRC), feed IntegrityTracker,
      enqueue to storage writer, post low-frequency progress UiEvent
DecodeWorker pool: SampleBatch → ProtocolDecoder.process → event store
AnalysisWorker pool: search/measure on demand, cancellable tokens
```

Rules (spec §8, enforced):

1. Widgets only on the GUI thread — by construction (workers only know
   `UiEventQueue`).
2. All cross-thread queues bounded with explicit backpressure; overflow is an
   integrity flag, never silent loss.
3. No blocking waits for USB/files in callbacks — `execute()` only touches
   in-memory state in Phase 1; Phase 3 USB opens move to DeviceWorker.
4. `multiprocessing` is deferred until profiling (Phase 17) proves the GIL is
   the bottleneck; NumPy vectorization covers the first decoding generations.

## 7. Teensy 4.1 firmware architecture (Phase 2 design)

```
hal/        mclk 600 MHz, GPIO ports, kDIO pin mux, DMA channels,
            free-running timer (µs counter), USB device stack
capture/    double-buffered DMA ping-pong (2 × 64 KiB), ISR swap,
            per-block header {seq u32, sample_index u64, ts_us u32,
            overflow u8, crc16 u16} + payload (uint16 rows, 16 ch)
            overflow flag raised when a swap is missed
trigger/    hardware: GPIO match on up to 16 pins (PDB/DMA gate) +
            software fallback for complex specs (Phase 11 parity)
usb/        bulk in/out endpoints, framing per docs/capture_protocol.md,
            sequence + CRC-32, heartbeat, resume state (last seq)
app/        command state machine: IDLE → CONFIGURED → ARMED → CAPTURING
            → STOPPED; rejects commands from wrong state (host and device
            both validate; host is authoritative for session data)
```

- No RTOS in v1 (bare loop + ISR, deterministic DMA); FreeRTOS is an option
  if the command/USB complexity grows — a documented decision, not a default.
- 16 channels = one 16-bit read per sample; expansion to 24 channels = two
  16-bit reads (port split), documented as an option pending board design.
- **No claimed sample rates until Phase 2/17 measurements** (see §16).

## 8. USB packet protocol (Phase 3; docs/capture_protocol.md)

- Host→device command frames, device→host data frames, both little-endian.
- Capture frame (device→host):

```
offset size field
0      4    MAGIC      0x534E4946 ("SNIF")
4      1    VERSION    frame format version (1)
5      1    TYPE       0x01 capture, 0x10 hello, 0x11 status, 0xFF error
6      2    HEADER_LEN bytes (forward compatibility: readers skip trailing
             unknown fields up to HEADER_LEN; new fields only in the tail)
8      4    SEQ        u32 sequence (device-ordered)
12     8    TIMESTAMP  u64 device µs counter (wrap tracked by host)
20     8    SAMPLE_IDX u64 absolute sample index
28     2    CH_MASK    u16
30     4    RATE       u32 Hz
34     4    SAMPLES    u32 count
38     4    PAYLOAD_LEN
42     2    FLAGS      u16 (overflow/last/rate-change/truncated)
44     N    PAYLOAD    packed samples (see sample packing in §10)
44+N   4    CRC32      over bytes 0..44+N (IEEE, LE)
```

- Control messages: HELLO (version, capabilities), CONFIG, ARM/START/STOP,
  HEARTBEAT (throughput stats every 100 ms), ERROR (category + code).
- Reconnect: device persists last seq in RAM; on re-HELLO the host compares
  seq and records the gap in IntegrityReport (never silent, spec §12).
- Throughput: device HEARTBEAT carries bytes/s + drops; host cross-checks
  against wire time. The GUI shows both, labelled *measured*.

## 9. Timestamp strategy (spec §13)

- **Master timeline = integer sample index.** One per session.
  `t_s = (index − start_index) / rate` only at the display edge.
- Integer wall-clock: `t_ns = epoch_utc_ns + (index − start_index)·10⁹ // rate`
  (`Timeline.index_to_utc_ns`; exact when rate divides 10⁹).
- Device µs counter (`device_ts_us`) is **gap-detection only**, never the
  master timeline — it can wrap (32-bit → 4295 s) and drifts with DMA gaps.
- All decoded events, triggers, cursors, bookmarks, measurements store
  `(start_index, duration)` integers on the master timeline.
- Float64 µs gives ~230 s of 1 µs resolution — another reason integer-first.

## 10. Capture data model

- `CaptureBlock` (immutable, frozen dataclass): the atomic transport unit;
  fields per §8; `crc_ok` set by the transport; `flags` per `BlockFlags`.
- **Sample packing (host + device agree):** channel c = bit c (LSB = ch0);
  ≤8 channels → 1 byte/sample, 9-16 → 2 bytes/sample, little-endian.
  `pack_samples`/`unpack_samples` are numpy-vectorized per channel.
- `SampleBatch`: decoded window `(n, n_channels)` uint8 + timeline context —
  the decoder input. Batches are cut on block boundaries (Phase 5 may merge
  blocks for viewport efficiency; decoders stay stateless across batches
  except their own protocol state).
- In-session index: block list (seq → storage offset) + transaction index
  (Phase 4).

## 11. Decoder API (docs/decoder_api.md)

- Streaming: `process(SampleBatch) → list[DecodedEvent]`, `flush()` at EOS.
- `DecodedEvent` fields: protocol, event_type, start_index, duration,
  channel (logical name), fields (typed dict), payload, text,
  status (OK/WARNING/ERROR), errors. Status carries timing anomalies —
  a decoder that is unsure says so (§17, "errors" surfaced, not hidden).
- Channel mapping is configuration: decoders see logical names (SCK, MOSI…)
  mapped to physical indices by the engine; decoders never hard-code pins.
- Registry: class registration with **API version check** (same major),
  fresh instance per `create()`; built-ins Phase 7-10, plugins Phase 14.
- SPI/I2C/UART/CAN/LIN decode requirements (spec §19-22) are the acceptance
  criteria for Phases 7-10; CAN/LIN/RS485 require the transceiver-aware
  model (MCU GPIO ≠ physical bus, §22).

## 12. Trigger architecture (docs/trigger_engine.md)

- `TriggerSpec` (final in Phase 1): conditions + logic (AND/OR, v1 flat;
  tree extension reserved) + pre/post windows + mode (single/continuous/rearm).
- Condition kinds: EDGE, LEVEL, PATTERN, PULSE, TIMEOUT, BYTE_SEQUENCE,
  PROTOCOL_FIELD (the latter two consume decoder events — the trigger engine
  subscribes to both sample streams and event streams).
- Evaluation: `TriggerEngine.compile(spec) → CompiledTrigger` (stateless
  compile, O(1)/sample steady-state process) — pure Python + NumPy, fully
  unit-testable on synthetic `SampleBatch`es (no hardware, no Tkinter).
- Pre-trigger: the capture pipeline keeps a ring of `pre_trigger_samples`
  while armed; on fire, ring is flushed to storage, then post-trigger
  completes. Trigger position is a master-timeline sample index; the result
  is stored in the session and drawn as a waveform marker.
- Example (spec §29) maps to: `EDGE(1, rising) AND PATTERN(...) AND
  BYTE_SEQUENCE(spi, 9F) AND PROTOCOL_FIELD(...)` — composition is data.

## 13. Native file format `.usn` (Phase 4; docs/file_format.md)

- Magic `USN1`, u32 format version, header + trailer with CRC-32.
- Sections (all chunked, 64-bit offsets, per-chunk CRC-32):
  metadata TLVs (device, firmware, capabilities, channel map, timebase,
  trigger spec, decoder config) → block index → sample chunks (N blocks each)
  → transaction index chunks → bookmarks/annotations → analysis metadata →
  trailer (sizes + total CRC).
- Properties: streamable (append during capture, flush index at close),
  random-read (offset table; mmap for large files), **recoverable** (a bad
  chunk is skipped + reported in the session integrity, others readable),
  extensible (unknown TLVs preserved, unknown chunks skipped by size).
- Multi-GB captures never fully loaded: readers fetch chunk ranges; the GUI
  requests only the visible viewport.

## 14. Testing architecture

```
tests/unit           pure-Python: errors, config, logging, timeline,
                     sample_block, integrity, trigger spec, session,
                     registry, ui_queue, main_controller (no Tk import)
tests/integration    pipeline: simulator thread → manager → integrity →
                     storage; multi-thread ingest hammering
tests/protocol       golden files: capture.bin → decoder → expected.json
                     (auto-compared); per-protocol fixture generators
tests/performance    benchmarks + regression gates (Phase 17 suite, JSON
                     reports; spec §49 rules: measured, reproducible)
tests/gui            Tkinter smoke/flow tests; auto-skip without display
```

- `SimulatorDevice` is the deterministic stand-in for hardware (same
  `CaptureDevice` interface): known square waves on CH0-2 + LCG bit on CH3,
  identical payloads for identical configuration — golden-test friendly.
- Hardware-in-loop (Phase 16) uses `tools/signal_generator` + firmware
  self-test patterns; CI baseline runs with **zero hardware** (this is the
  current baseline: 99 tests, headless).
- Definition-of-done gates: new interface → unit tests in the same change;
  decoder → golden pair; pipeline change → integration + stress.

## 15. Performance strategy (docs/performance.md)

- **Vectorize first:** decoders/analysis operate on numpy arrays over whole
  batches (no per-sample Python loops in hot paths; the channel loop is ≤16).
- **Bounded everything:** every queue has a size and a documented
  backpressure behaviour (pause, flag, never drop silently).
- **Storage:** chunked + mmap; viewport-only reads; no full-capture loads.
- **GUI:** 50 ms pump, model snapshots (O(1) reads), waveform viewport +
  decimation + chunk cache (Phase 5) — the canvas never draws > screen samples.
- **Profile before optimizing** (spec §50): cProfile/line profiler on the
  real pipeline; native extensions (Cython/Numba/Rust) only after a measured
  bottleneck, and the core must keep working without them.
- **Measured, reproducible benchmarks** in `tests/performance` write JSON
  reports (machine, params, results); CI gates are regression gates.
  "Zero latency", "unlimited capture", "guaranteed X MS/s" are banned phrasings.

## 16. Hardware limitations (documented; **unverified**)

- Teensy 4.1: i.MX RT1062 @ 600 MHz, USB **2.0 High-Speed** (480 Mbit/s).
- 16 ch = 2 bytes/sample → 1 MS/s = **32 MB/s** sustained DMA + USB.
  Realistic Windows sustained bulk throughput is typically ~30-45 MB/s →
  1 MS/s is *likely* feasible; 2 MS/s needs optimization (compression or
  32-bit packing study); 5-40 MS/s **will exceed** a single HS bulk pipe and
  is NOT targetable in v1. 1/5/10/20/24/40 MS/s remain *potential targets
  to be verified on hardware* (spec §9) — none is claimed anywhere in this
  codebase; capabilities report `max_sample_rate_hz = None` until measured.
- 32-bit µs counter wraps at 4295 s → host wrap tracking (spec §13).
- DMA ping-pong removes sample-level gaps; block-level overflow is flagged
  (`BlockFlags.OVERFLOW`), counted by the integrity tracker, shown in GUI.
- GPIO-only capture: no ADC in v1; analog support is an *architecture
  reservation* (spec §34) — the unified timeline already has the slots, but
  the app never reports voltages from digital pins.

## 17. Risks

| # | Risk | Mitigation |
|---|------|-----------|
| R1 | Sustained USB throughput < sample rate | integrity flags + honest status; adaptive rate; compression study; **no silent loss** |
| R2 | Tkinter canvas too slow for dense waveforms | viewport + decimation + chunk cache (Phase 5); renderer is a replaceable subsystem (§23) |
| R3 | Decoder timing errors on non-ideal signals | per-event status WARNING/ERROR + tolerance config; never fabricate data |
| R4 | Windows USB driver reconnect flakiness | reconnect protocol (seq resume), heartbeats, DEVICE_ERROR surfacing |
| R5 | Scope creep (18 phases, many protocols) | phase gates with DoD (§56); decoders one at a time; spec §18 ordering |
| R6 | Silent data loss (the cardinal sin) | CRC + seq + overflow flags at every boundary; IntegrityReport mandatory in UI |
| R7 | Python GIL limits decode throughput | NumPy first; worker pool; multiprocessing after profiling (Phase 17) |
| R8 | Untrusted plugin/script code | versioned plugin API, isolated execution, no auto-run (§38/§52) |
| R9 | Multi-GB RAM blowup | chunked .usn, mmap, viewport-only reads, no full loads |

## 18. Phase 1 implementation plan (executed — this codebase)

Delivered:

1. Project: `pyproject.toml`, `requirements*.txt`, `LICENSE`, `.gitignore`,
   `config/default.json`, `app` package with the full module skeleton.
2. Core: structured errors (§45), TRACE logging + export (§46), validated
   config, integer master timeline (§13), CaptureBlock/pack/SampleBatch
   (§10/§11), IntegrityTracker with the §12 summary format, CaptureStorage
   ABC + memory reference, CaptureManager state machine + thread-safe ingest.
3. HAL: Device/CaptureDevice/DeviceCapabilities/DeviceManager (§14/§15) +
   deterministic SimulatorDevice; Transport ABC + registry/manager; USB stub
   that fails fast with an actionable error (Phase 3).
4. Protocol: final decoder API + versioned registry (§16/§17) — no decoders
   yet (Phases 7-9). Trigger: final spec model + engine interfaces (§28/§29)
   — evaluation engine in Phase 11. Session model (§35).
5. GUI: main window (menu/toolbar/status bar/4 panels, dark+light themes),
   command-driven controllers (zero logic in callbacks), UiEventQueue pump,
   observable models; GUI code is import-safe and testable headless.
6. Tests: 99 passing / 1 display-skipped (GUI smoke suite), including
   integration pipeline, multi-thread ingest, spec §12 integrity formats,
   decoder registry contract, trigger spec round-trips.

Explicitly NOT delivered (per spec §55): waveform engine, protocol decoders,
USB implementation, .usn persistence, firmware.

### Verification evidence (this change)

- `pytest`: **106 passed, 1 skipped** (GUI test, no display in sandbox), 0 failed.
- Headless app smoke: connect → 1 MS/s × 4 ch capture → stop → integrity OK.
- Syntax: `py_compile` clean across `app/` and `tests/`.
- GUI visual check requires a display (Windows target): `python -m app.main`.
