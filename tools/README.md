# tools/ (Phase 16+ — not yet implemented)

Command-line utilities that stay out of the GUI:

- `signal_generator/` — deterministic SPI/I2C/UART/GPIO waveform generators
  for hardware-in-loop tests (Phase 16); shares the simulator's pattern
  model so firmware self-tests and desktop golden files agree.
- `capture_converter/` — `.usn` ↔ BIN/CSV/VCD batch conversion (Phase 15).
- `diagnostics/` — diagnostics bundle assembly: logs + config + device state
  + version → zip (Phase 18).
