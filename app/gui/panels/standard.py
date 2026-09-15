"""Standard panel factories (Phase 1 placeholders for later-phase engines).

Each placeholder is clearly labelled with the phase that implements it — the
layout, not the engine, is what Phase 1 delivers (spec §55).
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk


def _palette(widget: tk.Widget) -> dict[str, str]:
    try:
        return widget.winfo_toplevel()._usn_palette
    except (tk.TclError, AttributeError):
        return {}


def _make_treeview(parent, columns, headings, widths):
    """Treeview where columns/headings/widths are a single source of truth —
    heading() can never reference an undeclared column (regression guard)."""
    tree = ttk.Treeview(parent, columns=columns, show="headings")
    for col, heading, width in zip(columns, headings, widths):
        tree.heading(col, text=heading)
        tree.column(col, width=width, anchor="w", stretch=False)
    return tree


DEVICE_COLUMNS = ("device", "state", "firmware")
DEVICE_HEADINGS = ("Device", "State", "Firmware")
# Column widths set the panel's REQUESTED width (the left pane is weight=0,
# so it keeps ~230 px initial width in the PanedWindow).
DEVICE_WIDTHS = (110, 60, 60)


def build_device_panel(parent: tk.Widget) -> tk.Widget:
    """Left: device / channel list (device management fills this in Phase 3+)."""
    frame = ttk.Frame(parent)
    tree = _make_treeview(frame, DEVICE_COLUMNS, DEVICE_HEADINGS, DEVICE_WIDTHS)
    tree.configure(height=12)
    tree.pack(fill="both", expand=True, padx=4, pady=4)
    frame.device_tree = tree  # type: ignore[attr-defined]
    return frame


def build_waveform_panel(parent: tk.Widget) -> tk.Widget:
    """Center: waveform placeholder. The real decimated viewport renderer
    arrives in Phase 5 (spec §23/§24) and replaces this canvas only."""
    frame = ttk.Frame(parent)
    p = _palette(parent)
    ttk.Label(
        frame,
        text="Waveform viewer — placeholder (Phase 5: viewport rendering, decimation, cursors)",
        style="Muted.TLabel",
    ).pack(anchor="w", padx=6, pady=(4, 0))
    canvas = tk.Canvas(frame, bg=p.get("canvas", "#141517"), highlightthickness=0)
    canvas.pack(fill="both", expand=True, padx=4, pady=4)
    track_color = p.get("muted", "#555a63")
    label_color = p.get("muted", "#9aa0a6")
    for i in range(16):
        y = 12 + i * 18
        canvas.create_line(48, y, 4000, y, fill=track_color)
        canvas.create_text(6, y, anchor="w", text=f"CH{i}", fill=label_color,
                           font=("Consolas", 8, "bold"))
    frame.waveform_canvas = canvas  # type: ignore[attr-defined]
    return frame


TRANSACTION_COLUMNS = (
    "index", "timestamp", "duration", "bus", "channel", "address",
    "direction", "length", "payload", "decoded", "status", "errors",
)
TRANSACTION_HEADINGS = (
    "Index", "Timestamp", "Duration", "Bus", "Channel", "Address / ID",
    "Dir", "Len", "Payload", "Decoded", "Status", "Errors",
)


def build_transactions_panel(parent: tk.Widget) -> tk.Widget:
    """Bottom: transaction table (virtualized table engine lands in Phase 12;
    column set is final per spec §26)."""
    frame = ttk.Frame(parent)
    ttk.Label(
        frame,
        text="Transaction table — placeholder (Phase 12: virtualized rows, search, jump-to-waveform)",
        style="Muted.TLabel",
    ).pack(anchor="w", padx=6, pady=(4, 0))
    widths = (95,) * len(TRANSACTION_COLUMNS)
    tree = _make_treeview(frame, TRANSACTION_COLUMNS, TRANSACTION_HEADINGS, widths)
    tree.configure(height=5)
    tree.pack(fill="both", expand=True, padx=4, pady=4)
    frame.transactions_tree = tree  # type: ignore[attr-defined]
    return frame


def build_inspector_panel(parent: tk.Widget) -> tk.Widget:
    """Right: inspector (decoder output Phase 6-10, measurements Phase 12,
    session info Phase 4)."""
    frame = ttk.Frame(parent)
    notebook = ttk.Notebook(frame)
    for title, text in (
        ("Decoder", "Protocol decoder output — Phases 6–10"),
        ("Measurements", "Measurement engine — Phase 12"),
        ("Session", "Session metadata — Phase 4 (.usn)"),
    ):
        tab = ttk.Frame(notebook)
        ttk.Label(tab, text=text, style="Muted.TLabel", padding=12).pack(expand=True)
        notebook.add(tab, text=title)
    notebook.pack(fill="both", expand=True, padx=4, pady=4)
    return frame
