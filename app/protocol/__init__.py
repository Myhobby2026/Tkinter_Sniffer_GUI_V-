"""Protocol decoder engine (layer L3).

Phase 6 implements the runtime; the API and registry are final now
(see docs/decoder_api.md). Concrete decoders (SPI/I2C/UART/CAN/LIN) land in
Phases 7-10 and as versioned plugins in Phase 14.
"""
from .decoder_api import (
    DECODER_API_VERSION,
    DecodedEvent,
    DecoderInfo,
    DecoderStatus,
    ProtocolDecoder,
    api_version_compatible,
)
from .decoder_registry import DecoderRegistry, default_registry

__all__ = [
    "DECODER_API_VERSION",
    "DecodedEvent",
    "DecoderInfo",
    "DecoderStatus",
    "ProtocolDecoder",
    "api_version_compatible",
    "DecoderRegistry",
    "default_registry",
]
