"""Capture session model (spec §35).

A session records everything needed to reproduce and interpret a capture.
Serialisation to the versioned .usn format lands in Phase 4 (see
docs/file_format.md); the model itself is final now.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any


def new_session_id() -> str:
    return uuid.uuid4().hex


def _now_utc_ns() -> int:
    return time.time_ns()


@dataclass
class CaptureSession:
    id: str = field(default_factory=new_session_id)
    created_at_utc_ns: int = field(default_factory=_now_utc_ns)

    # Device / firmware (spec §35)
    device_info: dict[str, Any] = field(default_factory=dict)
    firmware: dict[str, Any] = field(default_factory=dict)
    capabilities: dict[str, Any] = field(default_factory=dict)

    # Configuration
    channel_config: dict[str, Any] = field(default_factory=dict)
    sample_rate_hz: int = 0
    trigger: dict[str, Any] | None = None
    decoder_config: dict[str, Any] | None = None

    # Results / annotations
    integrity: dict[str, Any] = field(default_factory=dict)
    bookmarks: list[dict[str, Any]] = field(default_factory=list)
    annotations: list[dict[str, Any]] = field(default_factory=list)
    analysis: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "created_at_utc_ns": self.created_at_utc_ns,
            "device_info": self.device_info,
            "firmware": self.firmware,
            "capabilities": self.capabilities,
            "channel_config": self.channel_config,
            "sample_rate_hz": self.sample_rate_hz,
            "trigger": self.trigger,
            "decoder_config": self.decoder_config,
            "integrity": self.integrity,
            "bookmarks": self.bookmarks,
            "annotations": self.annotations,
            "analysis": self.analysis,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CaptureSession":
        known = {
            "id", "created_at_utc_ns", "device_info", "firmware", "capabilities",
            "channel_config", "sample_rate_hz", "trigger", "decoder_config",
            "integrity", "bookmarks", "annotations", "analysis",
        }
        unknown = sorted(set(data) - known)
        session = cls(
            id=str(data.get("id", new_session_id())),
            created_at_utc_ns=int(data.get("created_at_utc_ns", 0)),
            device_info=dict(data.get("device_info", {})),
            firmware=dict(data.get("firmware", {})),
            capabilities=dict(data.get("capabilities", {})),
            channel_config=dict(data.get("channel_config", {})),
            sample_rate_hz=int(data.get("sample_rate_hz", 0)),
            trigger=data.get("trigger"),
            decoder_config=data.get("decoder_config"),
            integrity=dict(data.get("integrity", {})),
            bookmarks=list(data.get("bookmarks", [])),
            annotations=list(data.get("annotations", [])),
            analysis=dict(data.get("analysis", {})),
        )
        if unknown:
            # Forward compatibility: preserve unknown keys, never drop data.
            session.analysis["_unknown_keys"] = {k: data[k] for k in unknown}
        return session
