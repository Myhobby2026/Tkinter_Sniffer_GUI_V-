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
    # Sizing policy (Tk 8.6-verified on Windows):
    #   * ttk::panedwindow accepts NO per-pane sizing options in 8.6
    #     (-width/-height are classic-tk-only and raise TclError), so pane
    #     sizes are controlled by REQUESTED SIZE + weight:
    #     weight=0 panes keep their requested size; weight=1 absorbs the rest.
    #   * Initial sizes therefore come from the panel contents' geometry
    #     (column widths, text) — see standard.py.
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
        top.add(left, weight=0)    # fixed: requested width (~240 px)
        top.add(center, weight=1)  # flexible: absorbs remaining width
        top.add(right, weight=0)   # fixed: requested width (~300 px)

        bottom = self._container(outer, "transactions", "Transactions")
        outer.add(top, weight=1)   # flexible: absorbs remaining height
        outer.add(bottom, weight=0)  # fixed: requested height (~240 px)
        return outer

    def _container(self, host: tk.Widget, panel_id: str, title: str) -> ttk.Labelframe:
        spec = self._specs[panel_id]
        frame = ttk.Labelframe(host, text=title)
        content = spec.build(frame)
        content.pack(fill="both", expand=True)
        self._widgets[panel_id] = content
        return frame
