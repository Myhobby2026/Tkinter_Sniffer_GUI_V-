import pytest

from app.errors import CaptureError
from app.trigger import (
    Edge,
    Logic,
    TriggerCondition,
    TriggerEngine,
    TriggerKind,
    TriggerMode,
    TriggerSpec,
    validate_spec,
)


def _spec() -> TriggerSpec:
    return TriggerSpec(
        name="ch1_rising_and_pattern",
        conditions=[
            TriggerCondition(kind=TriggerKind.EDGE, channel=1, params={"edge": "rising"}),
            TriggerCondition(kind=TriggerKind.PATTERN,
                             params={"value": "0000_0011", "mask": "1111_1111"}),
        ],
        logic=Logic.AND,
        pre_trigger_samples=1000,
        post_trigger_samples=4096,
        mode=TriggerMode.REARM,
    )


def test_json_roundtrip():
    spec = _spec()
    data = spec.to_dict()
    assert data["logic"] == "AND"
    assert data["mode"] == "rearm"
    assert data["conditions"][0] == {"kind": "edge", "channel": 1, "params": {"edge": "rising"}}
    restored = TriggerSpec.from_dict(data)
    assert restored.to_dict() == data


def test_validate_ok():
    validate_spec(_spec())  # must not raise


def test_validate_empty_conditions():
    with pytest.raises(CaptureError) as excinfo:
        validate_spec(TriggerSpec(conditions=[]))
    assert excinfo.value.code == "TRIGGER_EMPTY"


def test_validate_edge_needs_channel():
    spec = TriggerSpec(conditions=[TriggerCondition(kind=TriggerKind.EDGE)])
    with pytest.raises(CaptureError) as excinfo:
        validate_spec(spec)
    assert excinfo.value.code == "TRIGGER_BAD_CHANNEL"


def test_validate_bad_pre_trigger():
    spec = _spec()
    spec.pre_trigger_samples = -1
    with pytest.raises(CaptureError) as excinfo:
        validate_spec(spec)
    assert excinfo.value.code == "TRIGGER_BAD_WINDOW"


def test_from_dict_bad_kind():
    with pytest.raises(CaptureError) as excinfo:
        TriggerSpec.from_dict({"conditions": [{"kind": "quantum"}]})
    assert excinfo.value.code == "TRIGGER_BAD_KIND"


def test_from_dict_bad_logic():
    with pytest.raises(CaptureError) as excinfo:
        TriggerSpec.from_dict({"logic": "XOR"})
    assert excinfo.value.code == "TRIGGER_BAD_ENUM"


def test_edge_enum_values():
    assert {e.value for e in Edge} == {"rising", "falling", "any"}


def test_engine_interface_pinned():
    """Phase 11 must implement these exact methods (interface is final now)."""
    engine = TriggerEngine()
    with pytest.raises(NotImplementedError):
        engine.compile(_spec())
    # validate IS implemented now:
    engine.validate(_spec())
