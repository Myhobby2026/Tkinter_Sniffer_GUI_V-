# `.usn` native capture format (Phase 4)

Status: design baseline. Implementations must be lossless and recoverable;
the reader must never fail silently on a corrupt file.

## Goals

- versioned, extensible, streamable (append during capture)
- random read by block index (viewport, replay, export, diff)
- per-chunk integrity → partial corruption is *reported*, not fatal
- 64-bit offsets; multi-GB files never fully loaded into RAM (mmap)

## Layout (all little-endian)

```
┌────────────────────────────────────────────────────┐
│ FILE HEADER (64 B)                                 │
│   magic  "USN1" (4)                                │
│   format_version u32 = 1                           │
│   header_crc u32 (over this header, crc field=0)   │
│   metadata_section_offset u64                      │
│   block_index_offset    u64                        │
│   blocks_offset         u64                        │
│   txn_index_offset      u64                        │
│   annotations_offset    u64                        │
│   trailer_offset        u64                        │
│   reserved [16] u8                                  │
├────────────────────────────────────────────────────┤
│ METADATA: TLV stream                               │
│   each: type u16, length u32, bytes (optional      │
│   crc per TLV: type+length+payload)                │
│   types: session id, created_at, device_info,      │
│   firmware, capabilities, channel_config,          │
│   timebase {rate, epoch_ns, start_index},          │
│   trigger_spec (JSON), decoder_config (JSON),      │
│   integrity (JSON), user_comment                   │
│   unknown TLV types MUST be preserved verbatim     │
├────────────────────────────────────────────────────┤
│ BLOCK INDEX: (offset u64, seq u32, sample_index    │
│   u64, flags u16, crc32 u32) × n_blocks            │
├────────────────────────────────────────────────────┤
│ SAMPLE CHUNKS: chunk header {chunk_id u32,         │
│   n_blocks u32, payload_len u32, crc32 u32} +      │
│   n_blocks × capture frame bodies (payloads +      │
│   per-frame crc32)                                 │
│   chunk size target: 64 KiB (tunable)              │
├────────────────────────────────────────────────────┤
│ TRANSACTION INDEX (Phase 6+): event pointer chunks │
│   (block_offset, sample_index, event_type, decoder)│
├────────────────────────────────────────────────────┤
│ ANNOTATIONS: bookmarks, annotations (TLV/JSON)     │
├────────────────────────────────────────────────────┤
│ TRAILER: total size u64, n_blocks u32,             │
│   trailer_crc u32, magic                            │
└────────────────────────────────────────────────────┘
```

## Writer behaviour (capture in progress)

- Append sample chunks sequentially; flush block-index entries to a
  sidecar `.usn.idx` periodically (crash → partial file is openable:
  the reader scans chunk headers forward from `blocks_offset`).
- On clean close: write final index + trailer.

## Reader guarantees

- Open: verify header magic/version/trailer CRC; a missing trailer →
  "incomplete file" mode (use recovered chunks, show WARNING in GUI).
- Corrupt chunk: skip, count, report (`IntegrityReport`-style summary in the
  session panel); never abort the whole read.
- Unknown version (newer): open if the header layout is forward-compatible,
  else refuse with a clear "file from vN — update application" error.
