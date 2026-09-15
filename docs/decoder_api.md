# Decoder API (final — Phase 1)

Implemented in `app/protocol/decoder_api.py` + `decoder_registry.py`.
This is the contract every built-in decoder (Phases 7-10) and plugin
decoder (Phase 14) implements.

## Interfaces

```python
class ProtocolDecoder(ABC):
    @property
    def info(self) -> DecoderInfo          # id, name, api_version, version,
                                           # required_channels, config_defaults
    def configure(self, config: dict)      # raises DecoderError on bad config
    def reset(self)                        # clear state; callable any time
    def process(self, batch: SampleBatch) -> list[DecodedEvent]
    def flush(self) -> list[DecodedEvent]  # end-of-stream leftovers
```

`DecoderInfo.api_version` is semver-checked against the host
(`DECODER_API_VERSION`, currently `1.0`): same major = compatible.

## Event contract

`DecodedEvent` carries **everything** the GUI needs and nothing the decoder
must not see:

- `protocol`, `event_type` (stable strings, e.g. `start`, `data`, `stop`,
  `tx_word`, `rx_word`, `nack`, `error_frame`)
- `start_index`, `duration` — **integer master-timeline sample units**
- `channel` — logical name from the channel map (never a raw pin number)
- `fields` — typed, JSON-serializable (e.g. `{"addr": 80, "rw": "read"}`)
- `payload` — raw bytes where meaningful
- `text` — human-readable summary for tables/overlays
- `status` — `OK | WARNING | ERROR`: a decoder that is unsure about timing
  or quality MUST downgrade the status and list `errors`; it must not
  silently emit wrong data
- `errors` — actionable strings (e.g. "gap > 2 samples on SCK")

## Channel mapping

Configuration includes a `channel_map` (logical → physical index), e.g.
`{"SCK": 0, "MOSI": 1, "MISO": 2, "CS": 3}`. The engine resolves it; the
decoder receives `batch.samples` plus the map and works with logical names.

## Rules for decoder authors

1. Vectorize with NumPy over the batch; no per-sample Python loops in the
   hot path (≤16-channel loops are acceptable).
2. Emit events in `start_index` order; one `process()` call = one batch.
3. Keep per-decoder state minimal and `reset()`-able; decoders must be safe
   to reuse across captures after `reset()`.
4. Never import `tkinter`, `app.transport`, `app.core.storage`, or GUI
   modules (enforced by review + import tests in Phase 6).
5. Timing tolerances are configuration (default: sane for 1 µs–100 µs
   period signals), with WARNING status when exceeded.

## Golden tests (per decoder, Phase 7+)

```
tests/golden/<decoder>/capture.bin   →  reference raw blocks
tests/golden/<decoder>/expected.json →  expected DecodedEvent list
tests/protocol/test_<decoder>.py     →  compare (normalized) output
```
