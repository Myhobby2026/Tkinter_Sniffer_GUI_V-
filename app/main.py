"""Application entry point (spec §57 Phase 1: basic Tkinter application).

    python -m app.main            # run the GUI
    universal-sniffer             # console script (pyproject)
    universal-sniffer --version

Object graph (wired here, not in the GUI):

    config → logging → DeviceManager(+Simulator) + CaptureManager + storage
             → DeviceModel/CaptureModel + UiEventQueue → MainController
             → MainWindow(root, app)

``run()`` imports tkinter lazily so this module (and the whole non-GUI object
graph) can be imported and tested in headless environments.
"""
from __future__ import annotations

import argparse
from pathlib import Path

from . import APP_NAME, __version__
from .config import AppConfig, load_config
from .core.capture.capture_manager import CaptureManager
from .core.storage.memory import MemoryCaptureStorage
from .gui.controllers.main_controller import MainController
from .gui.models.capture_model import CaptureModel
from .gui.models.device_model import DeviceModel
from .gui.ui_queue import UiEventQueue
from .hal.device_manager import DeviceManager
from .hal.simulator import SimulatorDevice
from .logging_setup import LoggingConfig, setup_logging


class Application:
    """Owns the object graph; the GUI is a thin projection of its state."""

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or load_config()
        self.log = setup_logging(
            LoggingConfig(
                level=self.config.log_level,
                console=self.config.log_console,
                file=self.config.log_file,
                log_dir=self.config.log_dir,
            )
        )
        self.device_manager = DeviceManager()
        self.simulator = SimulatorDevice(
            sample_rate_hz=1_000_000,
            channel_count=4,
            block_samples=4096,
            real_time=True,
        )
        self.device_manager.register(self.simulator)
        self.capture_manager = CaptureManager()
        self.storage = MemoryCaptureStorage()
        self.device_model = DeviceModel()
        self.capture_model = CaptureModel()
        self.ui_queue = UiEventQueue()
        self.controller = MainController(
            device_manager=self.device_manager,
            capture_manager=self.capture_manager,
            storage=self.storage,
            device_model=self.device_model,
            capture_model=self.capture_model,
            ui_queue=self.ui_queue,
        )

    def status_dict(self) -> dict:
        return {
            "app": APP_NAME,
            "version": __version__,
            "config": self.config.to_dict(),
            "device": self.controller.device_status(),
            "capture": self.controller.capture_status(),
        }

    def run(self) -> None:
        """Create the Tk root and run the mainloop (GUI thread)."""
        import tkinter as tk  # lazy: keeps app.main importable headless

        from .gui.main_window import MainWindow

        root = tk.Tk()
        MainWindow(root, self)
        self.log.info("%s %s started", APP_NAME, __version__)
        root.mainloop()
        self.log.info("exited")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="universal-sniffer",
        description=f"{APP_NAME} — desktop logic analyzer / protocol analyzer",
    )
    parser.add_argument("--config", type=Path, default=None,
                        help="explicit config file (JSON)")
    parser.add_argument("--theme", default=None, choices=("dark", "light"),
                        help="override GUI theme")
    parser.add_argument("--version", action="store_true", help="print version and exit")
    args = parser.parse_args(argv)

    if args.version:
        print(f"{APP_NAME} {__version__}")
        return 0

    try:
        config = load_config(args.config)
    except Exception as exc:  # ConfigurationError and friends
        print(f"configuration error: {exc}")
        return 2
    if args.theme:
        config.gui_theme = args.theme

    app = Application(config)
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
