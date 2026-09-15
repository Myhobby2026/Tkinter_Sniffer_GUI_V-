"""Trigger engine (spec §28/§29, see docs/trigger_engine.md).

Phase 1: trigger *model* (specs, conditions, validation, JSON round-trip) and
the engine interfaces. The evaluating engine (compile/process) lands in
Phase 11 — it must be independent of Tkinter and testable on synthetic data.
"""
from .trigger_api import (
    CompiledTrigger,
    Edge,
    Logic,
    TriggerCondition,
    TriggerEngine,
    TriggerKind,
    TriggerMode,
    TriggerResult,
    TriggerSpec,
    validate_spec,
)

__all__ = [
    "CompiledTrigger",
    "Edge",
    "Logic",
    "TriggerCondition",
    "TriggerEngine",
    "TriggerKind",
    "TriggerMode",
    "TriggerResult",
    "TriggerSpec",
    "validate_spec",
]
