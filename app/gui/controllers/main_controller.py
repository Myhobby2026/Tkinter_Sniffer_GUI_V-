"""Central command router (spec §8/§43).

Pure Python — no Tkinter imports. Every menu/toolbar action becomes a
Command; the controller executes it against the app layer and reports results
through CommandResult + UiEvents. The GUI thread never blocks on hardware or
I/O: Phase 1 devices (the simulator) are thread-based and fast; Phase 3 USB
operations move to worker threads behind the same command surface.
"""
from __future__ import annotations

import platform
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

from ... import APP_NAME, __version__
from ...core.capture.capture_manager import (
    CaptureConfig,
    CaptureManager,
    CaptureState,
)
from ...core.storage.memory import MemoryCaptureStorage
from ...errors import SnifferError
from ...hal.capture_device import CaptureDevice
from ...hal.device_manager import DeviceManager
from ...logging_setup import LogNames, make_logger
from ..commands import Cmd, Command
from ..models.capture_model import CaptureModel
from ..models.device_model import DeviceModel
from ..ui_queue import (
    EVENT_CAPTURE,
    EVENT_DEVICE,
    EVENT_ERROR,
    EVENT_MESSAGE,
    EVENT_THEME,
    UiEventQueue,
)

log = make_logger(LogNames.APP)


@dataclass
class CommandResult:
    ok: bool
    message: str = ""
    data: dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.ok


Handler = Callable[[dict[str, Any]], CommandResult]


class MainController:
    def __init__(
        self,
        *,
        device_manager: DeviceManager,
        capture_manager: CaptureManager,
        storage: MemoryCaptureStorage,
        device_model: DeviceModel,
        capture_model: CaptureModel,
        ui_queue: UiEventQueue,
    ) -> None:
        self._dm = device_manager
        self._cm = capture_manager
        self._storage = storage
        self._device_model = device_model
        self._capture_model = capture_model
        self._ui = ui_queue

        self._handlers: dict[str, Handler] = {
            Cmd.DEVICE_CONNECT: self._cmd_device_connect,
            Cmd.DEVICE_DISCONNECT: self._cmd_device_disconnect,
            Cmd.DEVICE_REFRESH: self._cmd_device_refresh,
            Cmd.CAPTURE_START: self._cmd_capture_start,
            Cmd.CAPTURE_STOP: self._cmd_capture_stop,
            Cmd.SESSION_NEW: self._cmd_session_new,
            Cmd.FILE_OPEN: self._cmd_not_implemented,
            Cmd.FILE_SAVE_AS: self._cmd_not_implemented,
            Cmd.EXPORT_BIN: self._cmd_not_implemented,
            Cmd.EXPORT_CSV: self._cmd_not_implemented,
            Cmd.EXPORT_JSON: self._cmd_not_implemented,
            Cmd.VIEW_SET_THEME: self._cmd_set_theme,
            Cmd.HELP_ABOUT: self._cmd_about,
            Cmd.HELP_DIAGNOSTICS: self._cmd_diagnostics,
            Cmd.APP_QUIT: self._cmd_quit,
        }

    # --------------------------------------------------------------- routing
    def execute(self, command: Command) -> CommandResult:
        handler = self._handlers.get(command.name)
        if handler is None:
            return self._fail(f"unknown command: {command.name}", code="CMD_UNKNOWN")
        try:
            result = handler(dict(command.args))
        except SnifferError as exc:
            log.warning("command %s failed: %s", command.name, exc.message)
            return self._fail(exc.message, exc.to_dict())
        except Exception as exc:  # noqa: BLE001 — GUI must never crash on a command
            log.exception("command %s raised unexpectedly", command.name)
            return self._fail(f"unexpected error: {exc}", code="CMD_UNEXPECTED")
        if not result.ok:
            self._ui.post(EVENT_ERROR, error=result.data.get("error", result.message))
        return result

    # ------------------------------------------------------------- factories
    def _fail(self, message: str, error: dict[str, Any] | str | None = None,
              code: str | None = None) -> CommandResult:
        payload = error if isinstance(error, dict) else {"message": message, "code": code}
        self._capture_model.set(last_error=message)
        self._ui.post(EVENT_ERROR, error=payload)
        return CommandResult(False, message, {"error": payload})

    def _ok(self, message: str, **data: Any) -> CommandResult:
        return CommandResult(True, message, data)

    # -------------------------------------------------------------- devices
    def _cmd_device_connect(self, args: dict[str, Any]) -> CommandResult:
        device_id = str(args.get("device_id", ""))
        device = self._dm.connect(device_id)
        caps = device.capabilities()
        self._device_model.set_device(
            device_id=device.info.id,
            name=device.info.name,
            state=device.state.value,
            firmware_version=caps.firmware_version,
            hardware_revision=caps.hardware_revision,
            channel_count=caps.channel_count,
        )
        if isinstance(device, CaptureDevice):
            self._cm.attach(device, self._storage)
        self._ui.post(EVENT_DEVICE)
        log.info("connected device %s (%s)", device.info.name, caps.firmware_version)
        return self._ok(f"Connected to {device.info.name}")

    def _cmd_device_disconnect(self, args: dict[str, Any]) -> CommandResult:
        device_id = str(args.get("device_id", ""))
        if self._cm.state is CaptureState.RUNNING:
            return self._fail("stop the capture before disconnecting", code="CMD_BUSY")
        self._dm.disconnect(device_id)
        self._device_model.clear()
        self._ui.post(EVENT_DEVICE)
        return self._ok(f"Disconnected {device_id}")

    def _cmd_device_refresh(self, args: dict[str, Any]) -> CommandResult:
        # Phase 3: USB enumeration. Phase 1: re-emit current registry.
        self._ui.post(EVENT_DEVICE)
        return self._ok("Devices refreshed", count=len(self._dm.list_devices()))

    # -------------------------------------------------------------- capture
    def _cmd_capture_start(self, args: dict[str, Any]) -> CommandResult:
        device = self._cm.device
        if device is None:
            return self._fail("connect a capture device first", code="CMD_NO_DEVICE")
        caps = device.capabilities()
        channel_count = int(args.get("channel_count", caps.channel_count or 4))
        rate = int(args.get("sample_rate_hz", 1_000_000))
        config = CaptureConfig(sample_rate_hz=rate, channel_count=channel_count)
        self._cm.configure(config)
        self._cm.start()
        self._capture_model.set(
            state="running",
            block_count=0,
            byte_count=0,
            sample_rate_hz=rate,
            channel_count=channel_count,
            integrity_summary="OK",
            last_error="",
        )
        self._ui.post(EVENT_CAPTURE)
        log.info("capture started: %d Hz / %d ch", rate, channel_count)
        return self._ok(f"Capture started at {rate} Hz / {channel_count} ch")

    def _cmd_capture_stop(self, args: dict[str, Any]) -> CommandResult:
        summary = self._cm.stop()
        self._capture_model.set(
            state="stopped",
            block_count=summary.block_count,
            byte_count=summary.byte_count,
            integrity_summary=summary.integrity.summary,
            last_error="",
        )
        self._ui.post(EVENT_CAPTURE)
        log.info(
            "capture stopped: %d blocks, %d bytes, integrity %s",
            summary.block_count,
            summary.byte_count,
            summary.integrity.summary,
        )
        return self._ok(
            f"Capture stopped: {summary.block_count} blocks, "
            f"integrity {summary.integrity.summary}",
            summary=summary.to_dict(),
        )

    # --------------------------------------------------------------- session
    def _cmd_session_new(self, args: dict[str, Any]) -> CommandResult:
        if self._cm.state is CaptureState.RUNNING:
            return self._fail("stop the capture before starting a new session", code="CMD_BUSY")
        self._storage = MemoryCaptureStorage()
        device = self._cm.device
        if device is not None:
            self._cm.attach(device, self._storage)
        self._capture_model.reset()
        self._ui.post(EVENT_CAPTURE)
        return self._ok("New capture session")

    # ----------------------------------------------------------------- view
    def _cmd_set_theme(self, args: dict[str, Any]) -> CommandResult:
        theme = str(args.get("theme", "dark"))
        self._ui.post(EVENT_THEME, theme=theme)
        return self._ok(f"Theme set to {theme}", theme=theme)

    # ----------------------------------------------------------------- help
    def _cmd_about(self, args: dict[str, Any]) -> CommandResult:
        return self._ok("about", app=APP_NAME, version=__version__, python=platform.python_version())

    def _cmd_diagnostics(self, args: dict[str, Any]) -> CommandResult:
        return self._ok(
            "diagnostics",
            **{
                "app": APP_NAME,
                "version": __version__,
                "python": sys.version.split()[0],
                "device": self._device_model.snapshot().__dict__,
                "capture": self.capture_status(),
                "devices": [info.__dict__ for info in self._dm.list_devices()],
            },
        )

    def _cmd_quit(self, args: dict[str, Any]) -> CommandResult:
        return self._ok("quit")

    def _cmd_not_implemented(self, args: dict[str, Any]) -> CommandResult:
        return CommandResult(
            False,
            "not available yet (scheduled for a later phase — see docs/architecture.md)",
        )

    # -------------------------------------------------------------- queries
    def device_status(self) -> str:
        return self._device_model.describe()

    def device_model_snapshot(self):
        return self._device_model.snapshot()

    def capture_status(self) -> dict[str, Any]:
        stats = self._cm.live_stats()
        model = self._capture_model.snapshot()
        return {
            **stats,
            "integrity_summary": self._cm.integrity_report.summary,
            "sample_rate_hz": model.sample_rate_hz,
            "channel_count": model.channel_count,
            "last_error": model.last_error,
            "text": model.describe(),
        }
