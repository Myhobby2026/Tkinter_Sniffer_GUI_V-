"""Headless GUI surface tests (run everywhere, no display needed).

Builds the real MainWindow + all panels against the mock tkinter (tk_mock)
and drives the real command flow. Catches the two bug classes that real
tkinter only reports at runtime via TclError:

  1. invalid subcommands  — e.g. ttk PanedWindow has no 'paneconfigure'
  2. invalid values       — e.g. Treeview.heading() for an undeclared column

Complements the real-display suite in test_main_window.py.
"""
import sys
import time

import pytest

from tests.gui import tk_mock


@pytest.fixture
def tk():
    removed = tk_mock.install()
    try:
        yield sys.modules["tkinter"]
    finally:
        tk_mock.restore(removed)


def _build_window(tk):
    """Fresh Application + MainWindow against the mock tkinter."""
    import app.main
    from app.gui.main_window import MainWindow

    app = app.main.Application()
    root = tk.Tk()
    win = MainWindow(root, app)
    root.update()
    return app, root, win


# --------------------------------------------------------------- meta-tests
def test_mock_catches_bad_panedwindow_subcommand(tk):
    """Meta: the mock must reject what real Tk rejects (else tests are void)."""
    root = tk.Tk()
    pw = tk.ttk.PanedWindow(root)
    child = tk.ttk.Frame(pw)
    pw.add(child, weight=1)
    with pytest.raises(Exception):  # AttributeError from mock; TclError in real Tk
        pw.paneconfigure(child, width=100)
    # and the real vocabulary works:
    pw.configure(child, width=100, minsize=50)


def test_mock_catches_undeclared_treeview_column(tk):
    root = tk.Tk()
    tree = tk.ttk.Treeview(root, columns=("a", "b"))
    with pytest.raises(tk.TclError):
        tree.heading("device", text="Device")
    tree.heading("a", text="A")  # declared column is fine


# ------------------------------------------------------------- construction
def test_window_and_all_panels_build_headlessly(tk):
    from app.gui.panels import standard

    app, root, win = _build_window(tk)
    assert set(win._panel_widgets) == {"device", "waveform", "transactions", "inspector"}
    device_tree = win._panel_widgets["device"].device_tree
    assert device_tree["columns"] == standard.DEVICE_COLUMNS
    txn_tree = win._panel_widgets["transactions"].transactions_tree
    assert txn_tree["columns"] == standard.TRANSACTION_COLUMNS
    win._poll()
    # status bar widgets exist and carry text
    assert win._sb_device.cget("text")
    root.destroy()


def test_menu_and_toolbar_commands_registered(tk):
    app, root, win = _build_window(tk)
    # every menu/toolbar command goes through _on_command; drive the safe ones
    result = win._on_command(_cmd("help.about"))
    assert result.ok
    result = win._on_command(_cmd("help.diagnostics"))
    assert result.ok
    assert tk_mock.messagebox.calls  # About + Diagnostics dialogs recorded
    root.destroy()


# -------------------------------------------------------------------- flow
def _cmd(name, **args):
    from app.gui.commands import Command

    return Command(name, args)


def test_full_capture_flow_headlessly(tk):
    from app.hal.simulator import SIMULATOR_DEVICE_ID

    app, root, win = _build_window(tk)
    assert win._on_command(_cmd("device.connect", device_id=SIMULATOR_DEVICE_ID)).ok
    win._poll()
    assert win._panel_widgets["device"].device_tree.get_children()  # row inserted

    assert win._on_command(_cmd("capture.start")).ok
    time.sleep(0.08)  # real-time simulator produces a few 4096-sample blocks
    result = win._on_command(_cmd("capture.stop"))
    assert result.ok
    summary = result.data["summary"]
    assert summary["block_count"] >= 1
    assert summary["integrity"]["ok"] is True
    win._poll()
    assert "stopped" in win._sb_capture.cget("text")
    assert "OK" in win._sb_integrity.cget("text")
    root.destroy()


def test_theme_switch_and_error_path_headlessly(tk):
    from app.hal.simulator import SIMULATOR_DEVICE_ID

    app, root, win = _build_window(tk)
    assert win._on_command(_cmd("view.set_theme", theme="light")).ok
    win._poll()
    assert root._usn_palette["bg"] == "#f2f3f5"

    # start without a device → structured error surfaces in the status bar
    assert not win._on_command(_cmd("capture.start")).ok
    win._poll()
    assert "⚠" in win._sb_msg.cget("text")

    # connect, then refuse disconnect while idle-capture is not running
    assert win._on_command(_cmd("device.connect", device_id=SIMULATOR_DEVICE_ID)).ok
    assert win._on_command(_cmd("device.disconnect", device_id=SIMULATOR_DEVICE_ID)).ok
    win._poll()

    # clean shutdown path
    win._on_close()
    assert root.winfo_exists() == 0


def test_poll_reschedules_itself(tk):
    app, root, win = _build_window(tk)
    root.after_jobs_count = len(root._after_jobs)
    win._poll()
    assert len(root._after_jobs) == root.after_jobs_count + 1  # after() re-armed
