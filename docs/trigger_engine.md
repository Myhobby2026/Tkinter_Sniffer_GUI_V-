# Trigger architecture

Status: **spec model final (Phase 1)** — implemented in
`app/trigger/trigger_api.py`; the evaluating engine (compile/process) lands
in Phase 11 on top of these exact types.

## Spec model

```python
TriggerSpec(
    name,
    conditions: [ TriggerCondition(kind, channel, params) ],
    logic: AND | OR            # v1 flat; tree extension reserved
    pre_trigger_samples: int,  # ring buffer kept while armed
    post_trigger_samples: int,
    mode: single | continuous | rearm,
)
```

Condition kinds:

| kind | params | notes |
|------|--------|-------|
| `edge` | `edge: rising\|falling\|any` | channel required (0-15) |
| `level` | `level: high\|low` | channel required |
| `pattern` | `value`, `mask` (hex strings) | multi-channel digital match |
| `pulse` | `min_samples`, `max_samples` | width window on a channel |
| `timeout` | `samples` | quiescence: no edges for N samples |
| `byte_sequence` | `bus`, `bytes` | evaluated on decoded bus data |
| `protocol_field` | `protocol`, `field`, `op`, `value` | e.g. `uart.text contains "ERROR"` |

`validate_spec()` (implemented now) rejects empty specs, bad channels,
negative windows, unknown kinds — the trigger UI uses the same validator.
JSON round-trip (`to_dict`/`from_dict`) is tested; specs persist in `.usn`.

## Engine design (Phase 11)

- `TriggerEngine.compile(spec) → CompiledTrigger`: static compilation to a
  small per-channel state machine (edge detectors, width counters, pattern
  matchers); O(1) work per sample in steady state, NumPy-vectorized pattern
  ops where possible.
- `CompiledTrigger.process(batch) → TriggerResult | None`:
  `TriggerResult(absolute_index, batch_index, conditions_matched)`.
- `BYTE_SEQUENCE` / `PROTOCOL_FIELD` conditions subscribe to decoder events:
  the trigger engine consumes *both* the sample stream and the event stream
  (events carry master-timeline indices, so correlation is exact).

## Capture pipeline interaction

```
armed (pre-trigger ring, size = pre_trigger_samples)
   └─ fire at sample S
        → flush ring to storage (marked pre-trigger)
        → continue capturing post_trigger_samples
        → mode: single → stop · continuous → keep going · rearm → re-arm
```

- Trigger position `S` is stored in the session; the waveform view draws the
  marker; the transaction table can jump to it.
- The trigger engine is pure Python + NumPy: unit-tested on synthetic
  `SampleBatch` sequences with exact expected fire indices (no hardware,
  no Tkinter — spec §29 "independent of Tkinter").

## Example (spec §29)

```
CH1 rising edge  AND  SPI CS active  AND  MOSI == 0x9F  AND  MISO == 0xEF
```

= `EDGE(1, rising) AND LEVEL(CS, low) AND BYTE_SEQUENCE(spi, [9F])
  AND PROTOCOL_FIELD(spi, rx_byte, "==", 0xEF)` — composition is data, not
code.
