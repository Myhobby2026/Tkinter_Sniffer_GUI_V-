from app.session import CaptureSession, new_session_id


def test_session_defaults():
    session = CaptureSession()
    assert session.id
    assert session.created_at_utc_ns > 0
    assert session.bookmarks == []


def test_roundtrip_preserves_data():
    session = CaptureSession()
    session.sample_rate_hz = 1_000_000
    session.device_info = {"name": "sim"}
    session.trigger = {"name": "t", "conditions": []}
    session.integrity = {"ok": True, "summary": "OK"}
    session.bookmarks.append({"sample_index": 42, "label": "start of burst"})
    restored = CaptureSession.from_dict(session.to_dict())
    assert restored.to_dict() == session.to_dict()


def test_unknown_keys_preserved_not_dropped():
    data = CaptureSession().to_dict()
    data["future_field"] = {"x": 1}
    restored = CaptureSession.from_dict(data)
    assert restored.analysis["_unknown_keys"] == {"future_field": {"x": 1}}


def test_session_ids_unique():
    assert new_session_id() != new_session_id()
