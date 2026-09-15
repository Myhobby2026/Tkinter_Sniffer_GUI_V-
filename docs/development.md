# Development guide

## Environment

- Python **3.11+** (3.12+ recommended; target platform Windows 10/11 64-bit,
  Linux/macOS later).
- Tkinter ships with the OS Python install on Windows; on Debian/Ubuntu:
  `sudo apt install python3-tk`.

```bash
python -m venv .venv
.venv/bin/pip install -r requirements-dev.txt   # runtime + pytest
# or: pip install -e ".[dev]"
```

## Run

```bash
.venv/bin/python -m app.main                 # GUI (dark theme)
.venv/bin/python -m app.main --theme light
.venv/bin/python -m app.main --config my.json
.venv/bin/python -m app.main --version
```

First-run demo: **Devices → Connect: Simulator**, then **Capture → Start**.
The simulator produces deterministic 4-channel patterns at 1 MS/s; watch the
status bar (`Device / Capture / Capture Integrity`).

## Test

```bash
.venv/bin/python -m pytest                     # full headless baseline
.venv/bin/python -m pytest tests/unit -v       # unit only
.venv/bin/python -m pytest tests/gui           # GUI tests (skip w/o display)
```

Baseline at Phase 1: **99 passed, 1 skipped** (GUI test, needs a display).

## Conventions

- **Layers**: GUI → app → core → protocol → transport → hal (downward only).
  Shared-kernel data modules (`errors`, `config`, `logging_setup`,
  `core.timeline`, `core.sample_block`, `core.integrity`) may be imported by
  any layer — see `docs/architecture.md` §1.
- **No Tkinter outside** `app/gui/main_window.py`, `app/gui/theme.py`,
  `app/gui/panels/*`. Controllers/models are pure Python by design.
- **Errors**: raise `SnifferError` subclasses with a stable `code`; the GUI
  renders them; workers never raise into Tk.
- **Data integrity**: any new data path must update
  `IntegrityTracker`-visible state (CRC/seq/overflow) — no silent drops.
- **Timestamps**: integer sample indices on the master timeline; floats only
  at the display edge.
- **Capabilities**: the GUI enables features from `DeviceCapabilities` only;
  `max_sample_rate_hz=None` means unknown — never display a guess.

## Adding a protocol decoder (Phase 7+ checklist)

1. Subclass `ProtocolDecoder`; implement `info/configure/reset/process/flush`.
2. Work only with `SampleBatch` + logical channel names.
3. Register in `default_registry()`; add API version.
4. Golden pair `capture.bin` / `expected.json` + `tests/protocol/test_x.py`.
5. Update the decoder panel's available-decoders list (UI).

## Changing a stable interface

Per spec §54, report first: *Current Architecture → Problem → Proposed
Change → Benefits → Risks → Compatibility Impact → Testing Plan*. Then
bump the relevant version (decoder API / frame format / .usn version).
