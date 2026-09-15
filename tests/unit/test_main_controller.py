"""MainController tests — the full GUI command surface, headless (no Tkinter)."""
import time

import pytest

from app.core.capture.capture_manager import CaptureManager, CaptureState
from app.core.storage.memory import MemoryCaptureStorage
from app.gui.commands import Cmd, Command
from app.gui.controllers.main_controller import MainController
from app.gui.models.capture_model import CaptureModel
from app.gui.models.device_model import DeviceModel
from app.gui.ui_queue import EVENT_CAPTURE, EVENT_DEVICE, EVENT_ERROR, EVENT_THEME
from app.hal.device_manager import DeviceManager
from app.hal.simulator import SIMULATOR_DEVICE_ID, SimulatorDevice


@pytest.fixture
def parts(tmp_path, monkeypatch):
    monkeypatch.setenv("USN_CONFIG_DIR", str(tmp_path))
    dm = DeviceManager()
    sim = SimulatorDevice(
        sample_rate_hz=1_000_000, channel_count=4, block_samples=256,
        real_time=False, max_blocks=8,
    )
    dm.register(sim)
    cm = CaptureManager()
    storage = MemoryCaptureStorage()
    device_model = DeviceModel()
    capture_model = CaptureModel()
    from app.gui.ui_queue import UiEventQueue

    ui = UiEventQueue()
    ctrl = MainController(
        device_manager=dm,
        capture_manager=cm,
        storage=storage,
        device_model=device_model,
        capture_model=capture_model,
        ui_queue=ui,
    )
    return type("P", (), dict(
        dm=dm, sim=sim, cm=cm, storage=storage,
        device_model=device_model, capture_model=capture_model, ui=ui, ctrl=ctrl,
    ))


def test_connect_start_stop_full_cycle(parts):
    ctrl = parts.ctrl
    result = ctrl.execute(Command(Cmd.DEVICE_CONNECT, {"device_id": SIMULATOR_DEVICE_ID}))
    assert result.ok
    snap = parts.device_model.snapshot()
    assert snap.connected and snap.name.endswith("Simulator")
    assert snap.firmware_version == "sim-0.1.0"
    kinds = [e.kind for e in parts.ui.drain()]
    assert EVENT_DEVICE in kinds

    result = ctrl.execute(Command(Cmd.CAPTURE_START, {}))
    assert result.ok
    assert parts.cm.state is CaptureState.RUNNING
    assert parts.capture_model.snapshot().state == "running"
    time.sleep(0.1)  # simulator (max_blocks=8, no pacing) finishes quickly

    result = ctrl.execute(Command(Cmd.CAPTURE_STOP, {}))
    assert result.ok
    summary = result.data["summary"]
    assert summary["block_count"] == 8
    assert summary["integrity"]["ok"] is True
    assert summary["integrity"]["summary"] == "OK"
    assert parts.storage.block_count == 8
    assert parts.capture_model.snapshot().state == "stopped"
    assert EVENT_CAPTURE in [e.kind for e in parts.ui.drain()]


def test_start_without_device_fails(parts):
    result = parts.ctrl.execute(Command(Cmd.CAPTURE_STOP, {}))
    assert not result.ok
    assert parts.ctrl.execute(Command(Cmd.CAPTURE_START, {})).ok is False
    events = parts.ui.drain()
    assert any(e.kind == EVENT_ERROR for e in events)
    assert parts.capture_model.snapshot().last_error != ""


def test_stop_without_start_fails(parts):
    result = parts.ctrl.execute(Command(Cmd.CAPTURE_STOP, {}))
    assert not result.ok
    assert "not capturing" in result.message


def test_double_start_rejected(parts):
    assert parts.ctrl.execute(Command(Cmd.DEVICE_CONNECT, {"device_id": SIMULATOR_DEVICE_ID})).ok
    assert parts.ctrl.execute(Command(Cmd.CAPTURE_START, {})).ok
    result = parts.ctrl.execute(Command(Cmd.CAPTURE_START, {}))
    assert not result.ok
    parts.ctrl.execute(Command(Cmd.CAPTURE_STOP, {}))


def test_disconnect_refused_while_running(parts):
    parts.ctrl.execute(Command(Cmd.DEVICE_CONNECT, {"device_id": SIMULATOR_DEVICE_ID}))
    parts.ctrl.execute(Command(Cmd.CAPTURE_START, {}))
    time.sleep(0.02)
    result = parts.ctrl.execute(Command(Cmd.DEVICE_DISCONNECT, {"device_id": SIMULATOR_DEVICE_ID}))
    assert not result.ok
    assert "stop the capture" in result.message
    parts.ctrl.execute(Command(Cmd.CAPTURE_STOP, {}))


def test_disconnect_after_stop(parts):
    parts.ctrl.execute(Command(Cmd.DEVICE_CONNECT, {"device_id": SIMULATOR_DEVICE_ID}))
    result = parts.ctrl.execute(Command(Cmd.DEVICE_DISCONNECT, {"device_id": SIMULATOR_DEVICE_ID}))
    assert result.ok
    assert parts.device_model.snapshot().device_id == ""


def test_session_new(parts):
    parts.ctrl.execute(Command(Cmd.DEVICE_CONNECT, {"device_id": SIMULATOR_DEVICE_ID}))
    parts.ctrl.execute(Command(Cmd.SESSION_NEW, {}))
    old = parts.storage
    assert parts.cm.storage is not old
    # capture still works in the fresh session
    assert parts.ctrl.execute(Command(Cmd.CAPTURE_START, {})).ok
    time.sleep(0.05)
    result = parts.ctrl.execute(Command(Cmd.CAPTURE_STOP, {}))
    assert result.ok and result.data["summary"]["block_count"] == 8


def test_theme_command_posts_event(parts):
    result = parts.ctrl.execute(Command(Cmd.VIEW_SET_THEME, {"theme": "light"}))
    assert result.ok
    events = parts.ui.drain()
    theme_events = [e for e in events if e.kind == EVENT_THEME]
    assert theme_events and theme_events[0].data["theme"] == "light"


def test_about_and_diagnostics(parts):
    result = parts.ctrl.execute(Command(Cmd.HELP_ABOUT, {}))
    assert result.ok
    assert result.data["version"]
    diag = parts.ctrl.execute(Command(Cmd.HELP_DIAGNOSTICS, {}))
    assert diag.ok
    assert diag.data["app"] == "Universal Sniffer"
    assert "capture" in diag.data


def test_not_implemented_commands_are_clean_errors(parts):
    result = parts.ctrl.execute(Command(Cmd.FILE_OPEN, {}))
    assert not result.ok
    assert "not available yet" in result.message


def test_unknown_command(parts):
    result = parts.ctrl.execute(Command("frobnicate.now"))
    assert not result.ok
    assert "unknown command" in result.message


def test_capture_status_shape(parts):
    status = parts.ctrl.capture_status()
    for key in ("state", "block_count", "byte_count", "integrity_summary",
                "sample_rate_hz", "channel_count", "last_error", "text"):
        assert key in status
    assert status["state"] == "idle"
