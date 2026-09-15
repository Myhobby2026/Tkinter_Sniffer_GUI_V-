"""Structured error model (spec §45).

Every failure in the application is representable as a SnifferError with an
ErrorCategory, an optional stable machine-readable code, and a context dict.
The GUI renders these as actionable diagnostics; workers never raise into Tk.
"""
from __future__ import annotations

from enum import Enum
from typing import Any


class ErrorCategory(str, Enum):
    """Error categories (spec §45)."""

    DEVICE = "DEVICE_ERROR"
    USB = "USB_ERROR"
    CAPTURE = "CAPTURE_ERROR"
    BUFFER_OVERFLOW = "BUFFER_OVERFLOW"
    CRC = "CRC_ERROR"
    SEQUENCE_GAP = "SEQUENCE_GAP"
    DECODER = "DECODER_ERROR"
    PROTOCOL = "PROTOCOL_ERROR"
    FILE = "FILE_ERROR"
    PLUGIN = "PLUGIN_ERROR"
    SCRIPT = "SCRIPT_ERROR"
    CONFIGURATION = "CONFIGURATION_ERROR"


class SnifferError(Exception):
    """Base class for all structured application errors."""

    category: ErrorCategory = ErrorCategory.CAPTURE

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.context: dict[str, Any] = dict(context or {})

    def to_dict(self) -> dict[str, Any]:
        """JSON-safe representation for diagnostics and UI events."""
        return {
            "category": self.category.value,
            "code": self.code,
            "message": self.message,
            "context": self.context,
        }


class DeviceError(SnifferError):
    category = ErrorCategory.DEVICE


class USBError(SnifferError):
    category = ErrorCategory.USB


class CaptureError(SnifferError):
    category = ErrorCategory.CAPTURE


class BufferOverflowError(SnifferError):
    category = ErrorCategory.BUFFER_OVERFLOW


class CrcError(SnifferError):
    category = ErrorCategory.CRC


class SequenceGapError(SnifferError):
    category = ErrorCategory.SEQUENCE_GAP


class DecoderError(SnifferError):
    category = ErrorCategory.DECODER


class ProtocolError(SnifferError):
    category = ErrorCategory.PROTOCOL


class FileError(SnifferError):
    category = ErrorCategory.FILE


class PluginError(SnifferError):
    category = ErrorCategory.PLUGIN


class ScriptError(SnifferError):
    category = ErrorCategory.SCRIPT


class ConfigurationError(SnifferError):
    category = ErrorCategory.CONFIGURATION
