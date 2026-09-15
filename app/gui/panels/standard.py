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


def build_device_panel(parent: tk.Widget) -> tk.Widget:
    """Left: device / channel list (device management fills this in Phase 3+)."""
    frame = ttk.Frame(parent)
    tree = ttk.Treeview(frame, columns=("state", "firmware"), show="headings", height=12)
    tree.heading("device", text="Device")
    tree.heading("state", text="State")
    tree.heading("firmware", text="Firmware")
    tree.column("device", width=150, anchor="w", stretch=False)
    tree.column("state", width=80, anchor="w")
    tree.column("firmware", width=80, anchor="w")
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
    tree = ttk.Treeview(frame, columns=TRANSACTION_COLUMNS, show="headings", height=5)
    for col, heading in zip(TRANSACTION_COLUMNS, TRANSACTION_HEADINGS):
        tree.heading(col, text=heading)
        tree.column(col, width=95, anchor="w", stretch=False)
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
