"""Main window (spec §41): menu bar, toolbar, status bar, panel layout.

Threading rules (spec §8), enforced structurally:
    * Tkinter widgets are created and modified ONLY on the GUI thread.
    * Menu/toolbar callbacks contain NO logic — they build a Command and pass
      it to MainController.execute().
    * Worker results arrive as UiEvents; ``_poll`` (a root.after loop) is the
      only place worker state reaches widgets.
"""
from __future__ import annotations

import json
import tkinter as tk
from tkinter import messagebox, ttk

from .. import APP_NAME, __version__
from ..hal.simulator import SIMULATOR_DEVICE_ID
from . import theme
from .commands import Cmd, Command
from .panels import PanelManager, PanelSpec
from .panels import standard
from .ui_queue import (
    EVENT_CAPTURE,
    EVENT_DEVICE,
    EVENT_ERROR,
    EVENT_MESSAGE,
    EVENT_THEME,
    UiEvent,
)


class MainWindow:
    def __init__(self, root: tk.Tk, app) -> None:
        self.root = root
        self.app = app
        self._controller = app.controller
        self._ui = app.ui_queue

        root.title(app.config.window_title)
        root.minsize(1100, 680)
        theme.apply_theme(root, app.config.gui_theme)

        self._theme_var = tk.StringVar(value=app.config.gui_theme)
        self._build_menu()
        self._build_toolbar()
        body = ttk.Frame(root)
        body.pack(fill="both", expand=True)
        self._panels = PanelManager(body)
        self._panels.register(PanelSpec("device", "Devices", standard.build_device_panel))
        self._panels.register(PanelSpec("waveform", "Waveform", standard.build_waveform_panel))
        self._panels.register(PanelSpec("transactions", "Transactions", standard.build_transactions_panel))
        self._panels.register(PanelSpec("inspector", "Inspector", standard.build_inspector_panel))
        self._panels.build_layout()
        self._panel_widgets = self._panels.content_widgets()

        self._build_statusbar()
        self._refresh_device_tree()
        root.after(app.config.ui_poll_ms, self._poll)
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ menu
    def _build_menu(self) -> None:
        menubar = tk.Menu(self.root)

        m_file = tk.Menu(menubar, tearoff=0)
        m_file.add_command(label="New Session",
                           command=lambda: self._on_command(Command(Cmd.SESSION_NEW)))
        m_file.add_separator()
        m_file.add_command(label="Open Capture…", state="disabled")   # Phase 4
        m_file.add_command(label="Save As…", state="disabled")        # Phase 4
        m_file.add_separator()
        m_file.add_command(label="Quit", accelerator="Ctrl+Q",
                           command=lambda: self._on_command(Command(Cmd.APP_QUIT)))
        menubar.add_cascade(label="File", menu=m_file)
        self.root.bind_all("<Control-q>", lambda _e: self._on_close())

        m_view = tk.Menu(menubar, tearoff=0)
        for name in theme.THEME_NAMES:
            m_view.add_radiobutton(
                label=name.capitalize(),
                variable=self._theme_var,
                value=name,
                command=lambda n=name: self._on_command(Command(Cmd.VIEW_SET_THEME, {"theme": n})),
            )
        m_view.add_separator()
        m_view.add_command(label="Workspace Presets", state="disabled")  # Phase 12+
        menubar.add_cascade(label="View", menu=m_view)

        m_capture = tk.Menu(menubar, tearoff=0)
        m_capture.add_command(label="Start",
                              command=lambda: self._on_command(Command(Cmd.CAPTURE_START)))
        m_capture.add_command(label="Stop",
                              command=lambda: self._on_command(Command(Cmd.CAPTURE_STOP)))
        m_capture.add_separator()
        m_capture.add_command(label="Trigger…", state="disabled")       # Phase 11
        menubar.add_cascade(label="Capture", menu=m_capture)

        m_devices = tk.Menu(menubar, tearoff=0)
        m_devices.add_command(label="Refresh",
                              command=lambda: self._on_command(Command(Cmd.DEVICE_REFRESH)))
        m_devices.add_command(label=f"Connect: Simulator ({SIMULATOR_DEVICE_ID})",
                              command=lambda: self._on_command(
                                  Command(Cmd.DEVICE_CONNECT, {"device_id": SIMULATOR_DEVICE_ID})))
        m_devices.add_command(label="Disconnect",
                              command=lambda: self._on_command(
                                  Command(Cmd.DEVICE_DISCONNECT, {"device_id": SIMULATOR_DEVICE_ID})))
        menubar.add_cascade(label="Devices", menu=m_devices)

        m_help = tk.Menu(menubar, tearoff=0)
        m_help.add_command(label="Diagnostics…",
                           command=lambda: self._on_command(Command(Cmd.HELP_DIAGNOSTICS)))
        m_help.add_command(label=f"About {APP_NAME}",
                           command=lambda: self._on_command(Command(Cmd.HELP_ABOUT)))
        menubar.add_cascade(label="Help", menu=m_help)

        self.root.config(menu=menubar)

    # --------------------------------------------------------------- toolbar
    def _build_toolbar(self) -> None:
        toolbar = ttk.Frame(self.root)
        toolbar.pack(side="top", fill="x", padx=4, pady=2)
        ttk.Button(
            toolbar, text="Connect",
            command=lambda: self._on_command(
                Command(Cmd.DEVICE_CONNECT, {"device_id": SIMULATOR_DEVICE_ID})),
        ).pack(side="left", padx=(0, 4))
        ttk.Button(toolbar, text="Start",
                   command=lambda: self._on_command(Command(Cmd.CAPTURE_START))).pack(side="left", padx=4)
        ttk.Button(toolbar, text="Stop",
                   command=lambda: self._on_command(Command(Cmd.CAPTURE_STOP))).pack(side="left", padx=4)
        ttk.Separator(toolbar, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Button(toolbar, text="Save", state="disabled").pack(side="left", padx=4)  # Phase 4

    # ------------------------------------------------------------- statusbar
    def _build_statusbar(self) -> None:
        bar = ttk.Frame(self.root)
        bar.pack(side="bottom", fill="x")
        self._sb_device = ttk.Label(bar, text="Device: none")
        self._sb_device.pack(side="left", padx=(8, 16))
        self._sb_capture = ttk.Label(bar, text="Capture: idle")
        self._sb_capture.pack(side="left", padx=(0, 16))
        self._sb_integrity = ttk.Label(bar, text="Capture Integrity: OK")
        self._sb_integrity.pack(side="left", padx=(0, 16))
        self._sb_msg = ttk.Label(bar, text="")
        self._sb_msg.pack(side="right", padx=8)

    # -------------------------------------------------------------- commands
    def _on_command(self, command: Command) -> None:
        """View → application boundary: the ONLY path from widgets to logic."""
        result = self._controller.execute(command)
        if command.name == Cmd.HELP_ABOUT and result.ok:
            data = result.data
            messagebox.showinfo(
                APP_NAME,
                f"{data['app']} v{data['version']}\n\n"
                f"Python {data['python']}\n\n"
                "Professional desktop logic analyzer / protocol analyzer with a\n"
                "Teensy 4.1 capture bridge.\n\nPhase 1 — foundation.",
            )
        elif command.name == Cmd.HELP_DIAGNOSTICS and result.ok:
            messagebox.showinfo("Diagnostics", json.dumps(result.data, indent=2, default=str))
        elif command.name == Cmd.APP_QUIT and result.ok:
            self._on_close()

    # -------------------------------------------------------------- poll loop
    def _poll(self) -> None:
        """GUI-thread pump: drain worker events, refresh status (spec §8/§43)."""
        try:
            for event in self._ui.drain():
                self._handle_ui_event(event)
            status = self._controller.capture_status()
            self._sb_device.config(text=self._controller.device_status())
            self._sb_capture.config(text=status["text"])
            self._sb_integrity.config(text=f"Capture Integrity: {status['integrity_summary']}")
        finally:
            self.root.after(self.app.config.ui_poll_ms, self._poll)

    def _handle_ui_event(self, event: UiEvent) -> None:
        kind = event.kind
        if kind == EVENT_DEVICE:
            self._refresh_device_tree()
        elif kind == EVENT_THEME:
            theme_name = str(event.data.get("theme", "dark"))
            theme.apply_theme(self.root, theme_name)
        elif kind == EVENT_MESSAGE:
            self._sb_msg.config(text=str(event.data.get("text", "")))
        elif kind == EVENT_ERROR:
            error = event.data.get("error")
            text = error.get("message") if isinstance(error, dict) else str(error)
            self._sb_msg.config(text=f"⚠ {text}", style="Error.TLabel")
        elif kind == EVENT_CAPTURE:
            pass  # continuous refresh in _poll covers progress

    def _refresh_device_tree(self) -> None:
        tree = getattr(self._panel_widgets.get("device"), "device_tree", None)
        if tree is None:
            return
        tree.delete(*tree.get_children())
        for info, state in self.app.device_manager.devices():
            tree.insert("", "end", iid=info.id, values=(info.name, state.value, ""))
        active = self._controller.device_model_snapshot()
        if active.device_id:
            tree.selection_set(active.device_id)

    # ----------------------------------------------------------------- close
    def _on_close(self) -> None:
        try:
            self._controller.execute(Command(Cmd.CAPTURE_STOP))
        except Exception:  # noqa: BLE001 — closing must never crash
            pass
        self.app.log.info("shutting down")
        self.root.destroy()
