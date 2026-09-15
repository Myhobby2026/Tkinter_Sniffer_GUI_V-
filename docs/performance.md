# Performance strategy and measurement policy

Rules (spec §49/§50):

1. **Never** claim "zero latency", "unlimited capture", or a sample rate
   that has not been measured on hardware. Every number in user-facing
   docs/status must link to a reproducible benchmark.
2. Optimize **measured** bottlenecks only (cProfile first, then targeted
   work). Native extensions (Cython/Numba/Rust/C) are considered only after
   profiling, and the core must keep working without them.
3. Bounded buffers with explicit backpressure everywhere; overflow is a
   flagged condition, never silent loss.

## Strategy by subsystem

| Subsystem | First-line strategy |
|---|---|
| Sampling (firmware) | DMA ping-pong; 16 ch = one 16-bit read; overflow flag, never drop |
| USB ingest | bulk + framing; single ingest thread; bounded queues; CRC/seq at the edge |
| Storage | chunked .usn, mmap, random read by index; no full-capture loads |
| Decoders | NumPy vectorized over batches; per-channel loops ≤ 16 |
| Search/measure | vectorized; on-demand workers with cancellation |
| Waveform | viewport-only data, level-of-detail decimation, chunk cache; canvas draws ≤ screen samples |
| GUI pump | 50 ms `after` loop; O(1) model snapshots; no work in callbacks |

## Benchmark suite (Phase 17; `tests/performance/`)

| ID | Metric | Pass gate (regression) |
|----|--------|------------------------|
| `pipeline_ingest` | sustained blocks/s, MB/s (sim + USB) | ≥ prior release (JSON report) |
| `decoder_spi_1msps` | events/s, CPU% | no >10% regression |
| `waveform_render_16ch` | FPS @ 1k/10k/100k px viewport | no >10% regression |
| `search_large_capture` | time vs dataset size (10× steps) | sub-linear growth check |
| `usn_load_4gb` | first-block latency, RSS | RSS bounded (mmap check) |
| `ui_event_latency` | command → status update p50/p95 | < 150 ms p95 |

Reports: JSON with machine info, params, results → committed as data in
`tests/performance/reports/` for release notes.

## Current measured facts (Phase 1)

- Pipeline (simulator, 4 ch, 256-sample blocks, 4-thread ingest hammer):
  no lost blocks, integrity OK — see `tests/integration/test_pipeline_smoke.py`.
- GUI: no measurable work in callbacks (commands are in-memory only).
- Real hardware sample rate: **not yet measured** — by policy, unreported.
