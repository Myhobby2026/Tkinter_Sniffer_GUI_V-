"""Trigger model (spec §28/§29, see docs/trigger_engine.md).

The spec model is final in Phase 1 so it can be saved in sessions/.usn and
shown in the trigger UI. The evaluating engine (compile/process) is
implemented in Phase 11 on top of these exact types.

Design rules:
    * TriggerSpec is pure data (JSON-serializable) — no Tkinter, no threads.
    * A compiled trigger is a stateful evaluator fed with SampleBatches,
      independent of transport and GUI (spec §29).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, ClassVar

from ..core.sample_block import SampleBatch
from ..errors import CaptureError


class TriggerKind(str, Enum):
    EDGE = "edge"                  # rising / falling / any edge on a channel
    LEVEL = "level"                # high / low level on a channel
    PATTERN = "pattern"            # digital pattern across channels (mask)
    PULSE = "pulse"                # pulse width min/max
    TIMEOUT = "timeout"            # quiescence (no edges for N samples)
    BYTE_SEQUENCE = "byte_sequence"  # on a decoded bus
    PROTOCOL_FIELD = "protocol_field"  # decoder event field match


class Edge(str, Enum):
    RISING = "rising"
    FALLING = "falling"
    ANY = "any"


class Logic(str, Enum):
    AND = "AND"
    OR = "OR"


class TriggerMode(str, Enum):
    SINGLE = "single"       # fire once, capture until post-trigger complete
    CONTINUOUS = "continuous"  # keep capturing after post-trigger
    REARM = "rearm"         # fire once, then re-arm


@dataclass
class TriggerCondition:
    """One condition in a trigger expression.

    ``params`` is kind-specific, e.g.:
        EDGE:      {"edge": "rising"}
        LEVEL:     {"level": "high"}
        PATTERN:   {"value": "0001_1010", "mask": "1111_1111"}
        PULSE:     {"min_samples": 100, "max_samples": 1000}
        TIMEOUT:   {"samples": 5000}
        BYTE_SEQUENCE: {"bus": "spi", "bytes": "9F EF"}
        PROTOCOL_FIELD: {"protocol": "uart", "field": "text", "contains": "ERROR"}
    """

    kind: TriggerKind
    channel: int | None = None
    params: dict[str, Any] = field(default_factory=dict)

    _KINDS: ClassVar[tuple[str, ...]] = tuple(k.value for k in TriggerKind)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "channel": self.channel,
            "params": dict(self.params),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TriggerCondition":
        kind = data.get("kind")
        if kind not in cls._KINDS:
            raise CaptureError(
                f"unknown trigger condition kind '{kind}'", code="TRIGGER_BAD_KIND"
            )
        channel = data.get("channel")
        if channel is not None and (not isinstance(channel, int) or channel < 0):
            raise CaptureError("trigger channel must be a non-negative int", code="TRIGGER_BAD_CHANNEL")
        params = data.get("params", {})
        if not isinstance(params, dict):
            raise CaptureError("trigger params must be an object", code="TRIGGER_BAD_PARAMS")
        return cls(kind=TriggerKind(kind), channel=channel, params=dict(params))


@dataclass
class TriggerSpec:
    """A complete trigger configuration (serialisable into a session)."""

    name: str = "trigger"
    conditions: list[TriggerCondition] = field(default_factory=list)
    logic: Logic = Logic.AND
    pre_trigger_samples: int = 0
    post_trigger_samples: int = 0
    mode: TriggerMode = TriggerMode.SINGLE

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "conditions": [c.to_dict() for c in self.conditions],
            "logic": self.logic.value,
            "pre_trigger_samples": self.pre_trigger_samples,
            "post_trigger_samples": self.post_trigger_samples,
            "mode": self.mode.value,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "TriggerSpec":
        try:
            logic = Logic(data.get("logic", Logic.AND.value))
            mode = TriggerMode(data.get("mode", TriggerMode.SINGLE.value))
        except ValueError as exc:
            raise CaptureError(f"invalid trigger enum value: {exc}", code="TRIGGER_BAD_ENUM") from exc
        pre = data.get("pre_trigger_samples", 0)
        post = data.get("post_trigger_samples", 0)
        if not isinstance(pre, int) or pre < 0:
            raise CaptureError("pre_trigger_samples must be a non-negative int", code="TRIGGER_BAD_PRE")
        if not isinstance(post, int) or post < 0:
            raise CaptureError("post_trigger_samples must be a non-negative int", code="TRIGGER_BAD_POST")
        raw_conditions = data.get("conditions", [])
        if not isinstance(raw_conditions, list):
            raise CaptureError("conditions must be a list", code="TRIGGER_BAD_CONDITIONS")
        return cls(
            name=str(data.get("name", "trigger")),
            conditions=[TriggerCondition.from_dict(c) for c in raw_conditions],
            logic=logic,
            pre_trigger_samples=pre,
            post_trigger_samples=post,
            mode=mode,
        )


@dataclass
class TriggerResult:
    """Where and what matched, in master-timeline units."""

    absolute_index: int
    batch_index: int
    conditions_matched: tuple[str, ...] = ()

    def describe(self) -> str:
        matched = ", ".join(self.conditions_matched) or "conditions"
        return f"trigger at sample {self.absolute_index} ({matched})"


class CompiledTrigger:
    """Stateful evaluator produced by a TriggerEngine (Phase 11).

    process() must be callable at up to the full sample rate and must never
    allocate more than O(1) per sample in steady state.
    """

    def process(self, batch: "SampleBatch") -> "TriggerResult | None":
        raise NotImplementedError("TriggerEngine lands in Phase 11")

    def reset(self) -> None:
        raise NotImplementedError("TriggerEngine lands in Phase 11")


class TriggerEngine:
    """Compiles TriggerSpec → CompiledTrigger (Phase 11).

    Phase 1 pins the interface; implementations are unit-tested against
    synthetic SampleBatches (no hardware, no Tkinter).
    """

    def compile(self, spec: TriggerSpec) -> CompiledTrigger:  # pragma: no cover - Phase 11
        raise NotImplementedError("TriggerEngine lands in Phase 11")

    def validate(self, spec: TriggerSpec) -> None:
        validate_spec(spec)


def validate_spec(spec: TriggerSpec) -> None:
    """Static validation of a trigger spec (usable by UI and engine)."""
    if not spec.conditions:
        raise CaptureError("trigger spec needs at least one condition", code="TRIGGER_EMPTY")
    if spec.pre_trigger_samples < 0 or spec.post_trigger_samples < 0:
        raise CaptureError("trigger pre/post samples must be >= 0", code="TRIGGER_BAD_WINDOW")
    for condition in spec.conditions:
        if condition.kind in (TriggerKind.EDGE, TriggerKind.LEVEL, TriggerKind.PULSE) and (
            condition.channel is None or not 0 <= condition.channel <= 15
        ):
            raise CaptureError(
                f"condition '{condition.kind.value}' needs a channel 0..15",
                code="TRIGGER_BAD_CHANNEL",
            )
        if condition.kind is TriggerKind.EDGE and condition.params.get("edge", "any") not in (
            Edge.RISING.value,
            Edge.FALLING.value,
            Edge.ANY.value,
        ):
            raise CaptureError("edge must be rising/falling/any", code="TRIGGER_BAD_EDGE")
