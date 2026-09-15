"""GUI smoke tests (spec §47: GUI tests where practical).

Skipped automatically when tkinter or a display is unavailable (headless CI).
"""
import time

import pytest

tk = pytest.importorskip("tkinter")


@pytest.fixture
def root():
    try:
        r = tk.Tk()
    except tk.TclError as exc:  # no display
        pytest.skip(f"no display available: {exc}")
    r.update_idletasks()
    yield r
    if r.winfo_exists():
        r.destroy()


@pytest.fixture
def app(monkeypatch, tmp_path):
    # avoid modal dialogs in tests
    monkeypatch.setattr("app.gui.main_window.messagebox",
                        type("M", (), {"showinfo": staticmethod(lambda *a, **k: None)}))
    monkeypatch.setenv("USN_CONFIG_DIR", str(tmp_path))
    from app.main import Application

    return Application()


def test_window_builds_with_all_panels(root, app):
    from app.gui.main_window import MainWindow
    from app.gui.panels import standard

    win = MainWindow(root, app)
    root.update()
    widgets = win._panel_widgets
    assert set(widgets) == {"device", "waveform", "transactions", "inspector"}
    assert widgets["device"].device_tree is not None
    assert widgets["transactions"].transactions_tree is not None
    root.update_idletasks()
    win._poll()


def test_treeview_columns_are_consistent(root, app):
    """Regression: every heading()/column() target must be a declared column
    (this failed with TclError 'Invalid column index device' on first run)."""
    from app.gui.main_window import MainWindow
    from app.gui.panels import standard

    win = MainWindow(root, app)
    root.update()
    device_tree = win._panel_widgets["device"].device_tree
    assert device_tree["columns"] == standard.DEVICE_COLUMNS
    n = len(standard.DEVICE_COLUMNS)
    assert n == len(standard.DEVICE_HEADINGS) == len(standard.DEVICE_WIDTHS)
    # heading() for each declared column must resolve without TclError
    for col in standard.DEVICE_COLUMNS:
        device_tree.heading(col)
    txn_tree = win._panel_widgets["transactions"].transactions_tree
    assert txn_tree["columns"] == standard.TRANSACTION_COLUMNS
    for col in standard.TRANSACTION_COLUMNS:
        txn_tree.heading(col)


def test_full_gui_flow_connect_capture_stop(root, app):
    from app.gui.commands import Cmd, Command
    from app.gui.main_window import MainWindow
    from app.hal.simulator import SIMULATOR_DEVICE_ID

    win = MainWindow(root, app)
    root.update()

    result = win._on_command(Command(Cmd.DEVICE_CONNECT, {"device_id": SIMULATOR_DEVICE_ID}))
    assert result.ok
    win._poll()
    root.update()
    assert "Simulator" in win._sb_device.cget("text")
    rows = win._panel_widgets["device"].device_tree.get_children()
    assert len(rows) == 1

    result = win._on_command(Command(Cmd.CAPTURE_START, {}))
    assert result.ok
    # simulator runs real-time (1 MS/s, 4096-sample blocks) — let it fill ~50 ms
    time.sleep(0.1)
    win._poll()
    root.update()

    result = win._on_command(Command(Cmd.CAPTURE_STOP, {}))
    assert result.ok
    win._poll()
    root.update()
    assert "stopped" in win._sb_capture.cget("text")
    assert "OK" in win._sb_integrity.cget("text")
    summary = result.data["summary"]
    assert summary["block_count"] >= 1
    assert summary["integrity"]["ok"] is True


def test_theme_switch_updates_style(root, app):
    from app.gui.commands import Cmd, Command
    from app.gui.main_window import MainWindow

    win = MainWindow(root, app)
    root.update()
    result = win._on_command(Command(Cmd.VIEW_SET_THEME, {"theme": "light"}))
    assert result.ok
    win._poll()
    root.update()
    assert root._usn_palette["bg"] == "#f2f3f5"


def test_error_shown_in_status_bar(root, app):
    from app.gui.commands import Cmd, Command
    from app.gui.main_window import MainWindow

    win = MainWindow(root, app)
    root.update()
    win._on_command(Command(Cmd.CAPTURE_START, {}))  # no device connected
    win._poll()
    root.update()
    assert "⚠" in win._sb_msg.cget("text")
