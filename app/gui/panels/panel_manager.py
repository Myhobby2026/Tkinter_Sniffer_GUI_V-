"""Panel scaffolding (spec §41).

Phase 1 uses a fixed ttk.PanedWindow layout:

    Main Window
    ├── Menu Bar / Toolbar / Status Bar
    ├── Left:   Device / Channel Tree
    ├── Center: Waveform
    ├── Bottom: Transaction Table
    └── Right:  Inspector / Decoder / Measurements

Panels are registered by id and built through a factory, so a more advanced
docking library can replace the layout later without touching the engine
(spec §41 last paragraph).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import tkinter as tk
from tkinter import ttk


@dataclass(frozen=True)
class PanelSpec:
    id: str
    title: str
    build: Callable[[ttk.Widget], tk.Widget]  # returns the panel's content widget


class PanelManager:
    def __init__(self, parent: tk.Widget) -> None:
        self._parent = parent
        self._specs: dict[str, PanelSpec] = {}
        self._widgets: dict[str, tk.Widget] = {}

    def register(self, spec: PanelSpec) -> None:
        if spec.id in self._specs:
            raise ValueError(f"panel '{spec.id}' already registered")
        self._specs[spec.id] = spec

    def content_widgets(self) -> dict[str, tk.Widget]:
        """id → content widget (after build_layout)."""
        return dict(self._widgets)

    # ---------------------------------------------------------------- layout
    _LEFT_WIDTH = 240
    _RIGHT_WIDTH = 300
    _BOTTOM_HEIGHT = 240

    def build_layout(self) -> ttk.PanedWindow:
        outer = ttk.PanedWindow(self._parent, orient=tk.VERTICAL)
        outer.pack(fill="both", expand=True)

        top = ttk.PanedWindow(outer, orient=tk.HORIZONTAL)
        left = self._container(top, "device", "Devices")
        center = self._container(top, "waveform", "Waveform")
        right = self._container(top, "inspector", "Inspector")
        top.add(left, weight=0)
        top.add(center, weight=1)
        top.add(right, weight=0)
        # ttk::panedwindow: per-pane options go through pane(pane, ...) —
        # NOT configure(pane, ...) (that is consumed as an options dict by
        # the inherited tk PanedWindow.configure) and NOT 'paneconfigure'
        # (a classic-tk-only subcommand that doesn't exist in ttk).
        top.pane(left, width=self._LEFT_WIDTH, minsize=180)
        top.pane(right, width=self._RIGHT_WIDTH, minsize=220)

        bottom = self._container(outer, "transactions", "Transactions")
        outer.add(top, weight=3)
        outer.add(bottom, weight=1)
        outer.pane(bottom, height=self._BOTTOM_HEIGHT, minsize=140)
        return outer

    def _container(self, host: tk.Widget, panel_id: str, title: str) -> ttk.Labelframe:
        spec = self._specs[panel_id]
        frame = ttk.Labelframe(host, text=title)
        content = spec.build(frame)
        content.pack(fill="both", expand=True)
        self._widgets[panel_id] = content
        return frame
