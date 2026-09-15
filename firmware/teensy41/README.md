# Teensy 4.1 firmware (Phase 2 — not yet implemented)

Design baseline lives in `docs/architecture.md` §7. No C code exists in
Phase 1 by design (spec §55: firmware starts in Phase 2).

## Planned layout

```
firmware/teensy41/
├── src/        main loop, command state machine (IDLE→CONFIGURED→ARMED→CAPTURING→STOPPED)
├── hal/        clock (600 MHz), GPIO/pin mux, DMA, free-running µs timer, USB glue
├── capture/    double-buffered DMA ping-pong (2 × 64 KiB), per-block
│               header {seq u32, sample_index u64, ts_us u32, overflow u8,
│               crc16 u16}, overflow flag on missed swap
├── dma/        channel config, ping-pong ISR swap
├── usb/        bulk endpoints, framing per docs/capture_protocol.md,
│               sequence + CRC-32, heartbeat, resume (last seq)
├── trigger/    hardware GPIO-match assist + software fallback (Phase 11 parity)
└── tests/      self-test patterns for hardware-in-loop (Phase 16)
```

## Ground rules

- No claimed sample rates until measured (Phase 2 bring-up + Phase 17).
  The desktop's `DeviceCapabilities.max_sample_rate_hz` stays `None` until
  a measurement exists.
- Overflow is flagged per block (`OVERFLOW`), never silently dropped.
- The host is authoritative for session data; the device validates state.
- Build toolchain: Arduino/Teensyduino or PlatformIO — chosen at Phase 2
  kickoff; board file targets `teensy41`.

## Verification plan (Phase 2/16)

- Deterministic on-board patterns (square waves, LCG bit) compared against
  the desktop `SimulatorDevice` golden outputs.
- `tools/signal_generator` drives known SPI/I2C/UART waveforms for HIL
  decoding/timing/trigger verification (Phase 16).
- Overflow behavior tested at rates above the verified maximum.
