"""ttk theming (Phase 1: dark + light, spec §41 visual baseline)."""
from __future__ import annotations

import sys
import tkinter as tk
from tkinter import ttk

THEME_NAMES = ("dark", "light")

_PALETTES = {
    "dark": {
        "bg": "#1e1f22",
        "fg": "#d8d9db",
        "muted": "#9aa0a6",
        "accent": "#4f8cff",
        "canvas": "#141517",
        "selection": "#2d5c99",
        "error": "#e05555",
    },
    "light": {
        "bg": "#f2f3f5",
        "fg": "#1c1d1f",
        "muted": "#5f6368",
        "accent": "#2f6fed",
        "canvas": "#ffffff",
        "selection": "#b8d0f5",
        "error": "#c0392b",
    },
}


def _default_font() -> tuple[str, int]:
    if sys.platform == "win32":
        return ("Segoe UI", 9)
    if sys.platform == "darwin":
        return ("Helvetica Neue", 11)
    return ("DejaVu Sans", 9)


def palette(name: str) -> dict[str, str]:
    if name not in _PALETTES:
        raise ValueError(f"unknown theme '{name}'; expected one of {THEME_NAMES}")
    return _PALETTES[name]


def apply_theme(root: tk.Tk, name: str = "dark") -> None:
    """Apply a theme to the main window. Safe to re-apply (theme switch)."""
    p = palette(name)
    font = _default_font()
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=p["bg"])
    root._usn_palette = p  # read by canvas-based placeholder panels

    style.configure(".", background=p["bg"], foreground=p["fg"], font=font)
    style.configure("TFrame", background=p["bg"])
    style.configure("TLabel", background=p["bg"], foreground=p["fg"])
    style.configure("Muted.TLabel", background=p["bg"], foreground=p["muted"])
    style.configure("Error.TLabel", background=p["bg"], foreground=p["error"])
    style.configure("Accent.TLabel", background=p["bg"], foreground=p["accent"],
                    font=(font[0], font[1] + 1, "bold"))
    style.configure("TLabelframe", background=p["bg"], foreground=p["fg"])
    style.configure("TLabelframe.Label", background=p["bg"], foreground=p["fg"])
    style.configure("TButton", focuscolor=p["bg"], padding=(8, 3))
    style.configure("TEntry", fieldbackground=p["canvas"], foreground=p["fg"])
    style.configure("TProgressbar", background=p["accent"], troughcolor=p["canvas"])
    style.configure("TSeparator", background=p["muted"])

    style.configure("Treeview", background=p["canvas"], fieldbackground=p["canvas"],
                    foreground=p["fg"], rowheight=22, borderwidth=0)
    style.configure("Treeview.Heading", background=p["bg"], foreground=p["fg"],
                    relief="flat", padding=(6, 4))
    style.map("Treeview",
              background=[("selected", p["selection"])],
              foreground=[("selected", p["fg"])])

    style.configure("TNotebook", background=p["bg"], bordercolor=p["bg"], tabmargins=(4, 4, 4, 0))
    style.configure("TNotebook.Tab", background=p["bg"], foreground=p["fg"], padding=(12, 4))
    style.map("TNotebook.Tab",
              background=[("selected", p["accent"])],
              foreground=[("selected", "#ffffff")])
    style.configure("TPanedwindow", background=p["bg"])
