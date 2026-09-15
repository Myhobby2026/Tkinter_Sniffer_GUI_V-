# Performance tests (Phase 17)

Benchmarks and regression thresholds live here. Rules (spec §49):

- Measure, never assume: sample rate, sustained throughput, decoder events/s,
  UI event latency, search time, file load time, memory.
- Every benchmark writes a JSON report (params + machine info + results).
- CI gates are **regression** gates (e.g. "pipeline ingest >= N MB/s"),
  not absolute marketing numbers.

Planned suite (Phase 17):

| Benchmark              | Metric                        | Tool            |
| ---------------------- | ----------------------------- | --------------- |
| pipeline_ingest        | blocks/s, MB/s sustained      | pytest + timer  |
| decoder_spi_1msps      | events/s, CPU%                | cProfile        |
| waveform_render_16ch   | FPS at 1k/10k/100k px view    | Tk test loop    |
| search_large_capture   | time vs dataset size (10x)    | pytest          |
| usn_load_4gb           | first block latency, RSS      | mmap profile    |
