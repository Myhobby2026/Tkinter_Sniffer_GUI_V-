"""Commands: the only way views talk to the application (spec §43).

Tkinter callbacks never contain logic — they build a Command and hand it to
the MainController. The controller is pure Python (no Tkinter).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Command:
    name: str
    args: dict[str, Any] = field(default_factory=dict)


class Cmd:
    # devices
    DEVICE_CONNECT = "device.connect"
    DEVICE_DISCONNECT = "device.disconnect"
    DEVICE_REFRESH = "device.refresh"
    # capture
    CAPTURE_START = "capture.start"
    CAPTURE_STOP = "capture.stop"
    # session / files
    SESSION_NEW = "session.new"
    FILE_OPEN = "file.open"
    FILE_SAVE_AS = "file.save_as"
    # export (Phase 15)
    EXPORT_BIN = "export.bin"
    EXPORT_CSV = "export.csv"
    EXPORT_JSON = "export.json"
    # view
    VIEW_SET_THEME = "view.set_theme"
    VIEW_TOGGLE_PANEL = "view.toggle_panel"
    # help / app
    HELP_ABOUT = "help.about"
    HELP_DIAGNOSTICS = "help.diagnostics"
    APP_QUIT = "app.quit"
