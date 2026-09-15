"""Storage engine (spec §36). The versioned .usn format lands in Phase 4;
this package defines the interface the rest of the core programs against.
"""
from .capture_storage import CaptureStorage
from .memory import MemoryCaptureStorage

__all__ = ["CaptureStorage", "MemoryCaptureStorage"]
