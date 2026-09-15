# USB Capture Protocol (device ↔ host)

Status: **design baseline for Phase 3**. Endianness: **little-endian** everywhere.
The host and device must both implement the exact byte layouts below; the
golden integration tests (Phase 3) compare captured frames against reference
vectors stored in `tests/golden/`.

## 1. Framing

- Transport: USB 2.0 High-Speed bulk endpoints (CDC-ACM serial in the
  fallback configuration for debugging; native bulk for data).
- Two logical channels multiplexed by frame `TYPE`:
  - control: HELLO, CONFIG, ARM, START, STOP, HEARTBEAT, ERROR
  - data: CAPTURE frames (the bulk of the traffic)
- A frame is self-describing: `HEADER_LEN` lets a forward-compatible reader
  skip unknown trailing header fields; `PAYLOAD_LEN` bounds the payload.

## 2. Capture frame (device → host)

```
offset  size  field        notes
──────  ────  ───────────  ──────────────────────────────────────────────
0       4     MAGIC        0x534E4946 ("SNIF"), LE
4       1     VERSION      frame format version (currently 1)
5       1     TYPE         0x01 CAPTURE
6       2     HEADER_LEN   header size in bytes incl. this field
8       4     SEQ          u32 sequence, starts at 0 per capture
12      8     TIMESTAMP    u64 device µs free-running counter
20      8     SAMPLE_IDX   u64 absolute sample index on master timeline
28      2     CH_MASK      u16 channels present (bit c = channel c)
30      4     RATE         u32 sample rate Hz
34      4     SAMPLES      u32 sample count in payload
38      4     PAYLOAD_LEN  u32 payload bytes
42      2     FLAGS        u16: 1=OVERFLOW 2=TRIGGER_FIRED 4=LAST
                           8=RATE_CHANGE 16=TRUNCATED
44      N     PAYLOAD      packed samples (channel c = bit c;
                           ≤8 ch: 1 B/sample; 9-16 ch: 2 B/sample)
44+N    4     CRC32        IEEE CRC-32 over bytes 0..44+N (LE)
```

Base header is 44 bytes; `HEADER_LEN >= 44`. New header fields are appended
before the payload and `HEADER_LEN` is increased — older hosts skip them.

## 3. Control frames (device → host unless noted)

| TYPE | name | payload |
|------|------|---------|
| 0x10 | HELLO | firmware_version u16, hw_rev u8, channel_count u8, usb_speed u8, last_seq u32 (resume), capabilities TLV blob |
| 0x11 | HEARTBEAT | ts_us u32, bytes_sent u32, blocks_sent u32, dma_drops u32, us |
| 0xFF | ERROR | category u8 (see `app/errors.py`), code u16, message len u8 + UTF-8 |
| 0x20 | CONFIG (host→device) | rate u32, ch_mask u16, trigger blob len + TLVs |
| 0x21 | START (host→device) | pre_trigger u32, post_trigger u32, mode u8 |
| 0x22 | STOP (host→device) | — (device replies with a LAST-flagged final block) |

## 4. Sequencing and integrity

- `SEQ` is strictly contiguous per capture; the host IntegrityTracker flags
  gaps/duplicates (spec §12). A gap is **data loss** and is reported, never
  hidden.
- `CRC32` failure → block counted as CRC error; payload still stored, marked
  `crc_ok=False` (analysis may use it, UI must warn).
- Device `OVERFLOW` flag (DMA/ring overflow) → counted and displayed.
- Disconnect + reconnect: HELLO carries `last_seq`; host records the missing
  range as blocks missing with a "device reconnect" context note.

## 5. Throughput

- HEARTBEAT every 100 ms carries the device's own throughput; the host
  cross-checks wire time. GUI shows **measured** values only.
- Theoretical USB HS bulk (≈ 60 MB/s) is **not** an application claim —
  sustained throughput is benchmarked on hardware (Phase 17) and published
  in `docs/performance.md` with the test rig description.
