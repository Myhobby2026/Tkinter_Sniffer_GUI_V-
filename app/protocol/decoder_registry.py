"""Decoder registry with API version checking (spec §16/§39)."""
from __future__ import annotations

from ..errors import DecoderError
from .decoder_api import (
    DECODER_API_VERSION,
    DecoderInfo,
    ProtocolDecoder,
    api_version_compatible,
)


class DecoderRegistry:
    """Holds decoder *classes*; create() hands out fresh instances."""

    def __init__(self) -> None:
        self._decoders: dict[str, tuple[type[ProtocolDecoder], DecoderInfo]] = {}

    def register(self, decoder_cls: type[ProtocolDecoder]) -> None:
        if not (isinstance(decoder_cls, type) and issubclass(decoder_cls, ProtocolDecoder)):
            raise DecoderError(
                "register() requires a ProtocolDecoder subclass", code="REGISTRY_BAD_CLASS"
            )
        probe = decoder_cls()
        info = probe.info
        if not api_version_compatible(info.api_version, DECODER_API_VERSION):
            raise DecoderError(
                f"decoder '{info.id}' API {info.api_version} is incompatible "
                f"with host API {DECODER_API_VERSION}",
                code="REGISTRY_API_MISMATCH",
            )
        if info.id in self._decoders:
            raise DecoderError(
                f"decoder '{info.id}' already registered", code="REGISTRY_DUP"
            )
        self._decoders[info.id] = (decoder_cls, info)

    def unregister(self, decoder_id: str) -> None:
        if decoder_id not in self._decoders:
            raise DecoderError(f"unknown decoder '{decoder_id}'", code="REGISTRY_UNKNOWN")
        del self._decoders[decoder_id]

    def get_info(self, decoder_id: str) -> DecoderInfo:
        try:
            return self._decoders[decoder_id][1]
        except KeyError:
            raise DecoderError(
                f"unknown decoder '{decoder_id}'", code="REGISTRY_UNKNOWN"
            ) from None

    def list_info(self) -> list[DecoderInfo]:
        return [info for _, info in sorted(self._decoders.values(), key=lambda t: t[1].id)]

    def create(self, decoder_id: str) -> ProtocolDecoder:
        try:
            decoder_cls, _ = self._decoders[decoder_id]
        except KeyError:
            raise DecoderError(
                f"unknown decoder '{decoder_id}'", code="REGISTRY_UNKNOWN"
            ) from None
        return decoder_cls()


_default_registry: DecoderRegistry | None = None


def default_registry() -> DecoderRegistry:
    """Process-wide registry. Built-in decoders register here in Phases 7-10;
    plugin decoders in Phase 14."""
    global _default_registry
    if _default_registry is None:
        _default_registry = DecoderRegistry()
    return _default_registry
