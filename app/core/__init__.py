"""Core engine (layer L4).

Modules:
    timeline/      master timeline (integer sample units, spec §13)
    sample_block   capture data model: blocks, packed samples, batches (§10/§11)
    integrity      capture integrity tracking (no silent data loss, spec §12)
    storage/       capture storage engine (spec §36; .usn lands in Phase 4)
    capture/       capture orchestration (state machine + pipeline glue)
    analysis/      (Phase 12)
    measurements/  (Phase 12)
    search/        (Phase 12)
    replay/        (Phase 4)

Shared-kernel rule: the pure data/logic modules above (timeline, sample_block,
integrity) may be imported by lower layers (hal, transport). Behaviour modules
(capture, storage implementations) may not.
"""
