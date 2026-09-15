# Universal Sniffer

Professional desktop **electronics sniffer / logic analyzer / protocol
analyzer** with a **Teensy 4.1** capture bridge. Python 3 + Tkinter/ttk
front end, modular C-free core engine, deterministic simulator for
hardware-free development.

> Status: **Phase 1 — Foundation** (of 18). The core engine, HAL, transport
> interfaces, decoder/trigger APIs, and a working Tkinter application shell
> are implemented and tested. Waveform rendering, protocol decoders, USB
> capture, and the `.usn` format arrive in later phases. No hardware sample
> rates are claimed anywhere — by policy, only *measured* numbers are
> published (see [docs/performance.md](docs/performance.md)).

## What exists today (Phase 1)

- **Application**: main window with menus, toolbar, status bar, four-panel
  workspace (devices / waveform placeholder / transactions placeholder /
  inspector), dark + light themes.
- **Capture pipeline (working, hardware-free)**: connect the built-in
  deterministic **simulator device** → start capture at 1 MS/s × 4 ch →
  blocks flow through a lock-guarded ingest → **integrity tracking**
  (sequence gaps, CRC errors, overflows — spec §12: no silent data loss) →
  session storage. Stop → summary with integrity verdict.
- **Core engine**: integer **master timeline** (§13), `CaptureBlock` /
  `SampleBatch` data model with vectorized pack/unpack (§10/§11),
  `CaptureStorage` interface + memory reference, `CaptureManager` state
  machine, structured **error model** (§45), **TRACE-level logging** with
  export (§46), validated **configuration**.
- **HAL + transport**: `Device` / `CaptureDevice` / `DeviceCapabilities` /
  `DeviceManager` (§14/§15 — the GUI enables features from *reported*
  capabilities only), `Transport` ABC + registry/manager, USB stub that
  fails fast until Phase 3.
- **Protocol + trigger APIs (final, no engines yet)**: versioned
  `ProtocolDecoder` contract + registry (§16/§17) and the full trigger
  spec model with validation + JSON round-trip (§28/§29); evaluation
  engines arrive in Phases 6-11 on these exact interfaces.
- **GUI architecture**: zero logic in callbacks — menus/toolbar emit
  `Command`s to a pure-Python controller; workers talk to the GUI only
  through a thread-safe `UiEventQueue` pumped at 50 ms (§8/§43).
- **Tests**: 106 passing / 1 display-skipped — unit, integration (real
  threading), protocol-contract, and GUI smoke suites; runs with **zero
  hardware** required.

## Quick start

```bash
python -m venv .venv
.venv/bin/pip install -r requirements.txt   # numpy + pyserial (Tkinter is built into Windows Python)
.venv/bin/python -m app.main                # GUI, from the repo root
.venv/bin/python app/main.py                # same — script mode works too
.venv/bin/python run.py --theme light       # convenience launcher
.venv/bin/python -m app.main --version
```

> Canonical form is `python -m app.main` from the repository root. Running
> `python main.py` from inside `app/` also works now (script-mode shim).
> The GUI needs the OS Python's Tk — on Windows it ships with python.org
> installs; on Debian/Ubuntu: `sudo apt install python3-tk`.

Then in the GUI: **Devices → Connect: Simulator** → **Capture → Start** →
watch the status bar → **Capture → Stop**.

```bash
.venv/bin/python -m pytest              # full test baseline (headless)
```

## Documentation

| Doc | Contents |
|-----|----------|
| [docs/architecture.md](docs/architecture.md) | Full architecture review: layers, interfaces, thread model, firmware, USB protocol, timestamps, file format, risks, phase plan |
| [docs/development.md](docs/development.md) | Environment, run, test, conventions, decoder checklist |
| [docs/capture_protocol.md](docs/capture_protocol.md) | USB frame format (Phase 3) |
| [docs/file_format.md](docs/file_format.md) | `.usn` format design (Phase 4) |
| [docs/decoder_api.md](docs/decoder_api.md) | Decoder contract + golden-test rules |
| [docs/trigger_engine.md](docs/trigger_engine.md) | Trigger spec model + engine design |
| [docs/performance.md](docs/performance.md) | Measurement policy + benchmark suite |

## Roadmap (spec phases)

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | Foundation: project, interfaces, logging, config, GUI shell, tests | ✅ done |
| 2 | Teensy GPIO capture: timer, DMA, ring buffer, overflow flags | next |
| 3 | USB transport: framing, CRC, seq validation, reconnect, throughput | |
| 4 | Capture session: timeline storage, `.usn`, replay | |
| 5 | Waveform: viewport rendering, decimation, zoom/pan, cursors | |
| 6 | Decoder framework runtime | |
| 7-9 | SPI · I2C · UART decoders | |
| 10 | CAN / LIN / RS485 (transceiver-aware) | |
| 11 | Trigger engine + UI (pre/post, patterns) | |
| 12 | Analysis: transaction table, search, measurements, statistics | |
| 13 | Hex / binary analysis, bitfields, diff | |
| 14 | Plugins + scripting | |
| 15 | Export: CSV/JSON/BIN/VCD/PCAP | |
| 16 | Hardware-in-loop validation | |
| 17 | Performance: profile, optimize, benchmark gates | |
| 18 | Release: packaging, installer, docs, regression | |

## Hardware

Primary: **Teensy 4.1** (16 synchronized digital channels; 24-channel
expansion reserved). Future: STM32, RP2040, FPGA, Ethernet capture device —
all behind the same HAL. CAN/LIN/RS485 require proper external transceivers;
an MCU GPIO is **not** a safe physical bus interface (spec §22).

Sample-rate targets (1/5/10/20/24/40 MS/s) are *potential* until measured on
hardware (spec §9) — see [docs/performance.md](docs/performance.md).

## License

MIT — see [LICENSE](LICENSE).
