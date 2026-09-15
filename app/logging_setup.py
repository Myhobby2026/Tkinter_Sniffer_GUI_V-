"""Centralised logging (spec §46).

- TRACE (5) .. CRITICAL levels.
- Namespaced loggers: usn.app, usn.device, usn.usb, usn.capture, usn.decoder,
  usn.storage, usn.plugins, usn.scripting.
- Console + rotating file output.
- export_logs() assembles a diagnostics bundle.
"""
from __future__ import annotations

import logging
import logging.handlers
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TRACE = 5
# addLevelName replaces any existing mapping for level 5 (on 3.11 it is
# "Level 5"; on 3.12+ the lookup returns the int). Safe to call unconditionally.
logging.addLevelName(TRACE, "TRACE")

LOG_FILE_NAME = "universal-sniffer.log"


class LogNames:
    """Canonical logger names (spec §46)."""

    ROOT = "usn"
    APP = "usn.app"
    DEVICE = "usn.device"
    USB = "usn.usb"
    CAPTURE = "usn.capture"
    DECODER = "usn.decoder"
    STORAGE = "usn.storage"
    PLUGINS = "usn.plugins"
    SCRIPTING = "usn.scripting"

    ALL = (APP, DEVICE, USB, CAPTURE, DECODER, STORAGE, PLUGINS, SCRIPTING)


def make_logger(name: str) -> logging.Logger:
    """Get a namespaced logger (e.g. make_logger(LogNames.CAPTURE))."""
    return logging.getLogger(name)


def trace(logger: logging.Logger, msg: str, *args: Any) -> None:
    """Emit at TRACE level (custom level, spec §46)."""
    if logger.isEnabledFor(TRACE):
        logger.log(TRACE, msg, *args)


@dataclass
class LoggingConfig:
    level: str = "INFO"
    console: bool = True
    file: bool = True
    log_dir: str | Path | None = None
    max_bytes: int = 5 * 1024 * 1024
    backup_count: int = 5
    format: str = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"


def setup_logging(config: LoggingConfig | None = None) -> logging.Logger:
    """Configure the 'usn' logger tree. Idempotent — safe to call twice.

    Returns the usn.app logger.
    """
    cfg = config or LoggingConfig()
    root = logging.getLogger(LogNames.ROOT)
    level_name = str(cfg.level).upper()
    # TRACE is a custom level (no logging.TRACE attribute exists)
    root.setLevel(TRACE if level_name == "TRACE" else getattr(logging, level_name, logging.INFO))
    root.handlers.clear()
    root.propagate = False

    formatter = logging.Formatter(cfg.format)
    if cfg.console:
        console = logging.StreamHandler()
        console.setFormatter(formatter)
        root.addHandler(console)
    if cfg.file and cfg.log_dir:
        log_dir = Path(cfg.log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_dir / LOG_FILE_NAME,
            maxBytes=cfg.max_bytes,
            backupCount=cfg.backup_count,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        root.addHandler(file_handler)
    return make_logger(LogNames.APP)


def flush_all() -> None:
    for handler in logging.getLogger(LogNames.ROOT).handlers:
        handler.flush()


def export_logs(dest_dir: str | Path, source_dir: str | Path | None = None) -> list[Path]:
    """Copy collected log files into a diagnostics bundle directory (spec §46/§51)."""
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    src = Path(source_dir) if source_dir else Path.cwd() / "logs"
    if not src.exists():
        return []
    written: list[Path] = []
    for path in sorted(src.glob(LOG_FILE_NAME + "*")):
        target = dest / path.name
        shutil.copy2(path, target)
        written.append(target)
    return written
