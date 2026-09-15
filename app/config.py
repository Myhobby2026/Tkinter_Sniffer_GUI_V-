"""Application configuration (spec: configuration).

Sources, in increasing precedence:
  1. embedded defaults (always available)
  2. bundled config/default.json (repo root)
  3. explicit --config path
  4. user config dir:  ~/.config/universal-sniffer/config.json (Linux)
                       %APPDATA%/universal-sniffer/config.json   (Windows)
  5. environment: USN_CONFIG_DIR (user dir override), USN_LOG_LEVEL

Unknown sections are ignored (forward compatibility); wrong types raise
ConfigurationError.
"""
from __future__ import annotations

import copy
import json
import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .errors import ConfigurationError

APP_NAME = "Universal Sniffer"
USER_APP_NAME = "universal-sniffer"
ENV_CONFIG_DIR = "USN_CONFIG_DIR"
ENV_LOG_LEVEL = "USN_LOG_LEVEL"

log = logging.getLogger("usn.app.config")

_DEFAULTS: dict[str, Any] = {
    "app": {"name": APP_NAME, "version": "0.1.0"},
    "gui": {"theme": "dark", "ui_poll_ms": 50, "window_title": APP_NAME},
    "logging": {"level": "INFO", "console": True, "file": True, "log_dir": "logs"},
    "paths": {"captures": "captures", "exports": "exports", "logs": "logs"},
}

# Known keys and their required types (validated, spec §52: validate inputs).
_SCHEMA: dict[str, dict[str, type]] = {
    "gui": {"theme": str, "ui_poll_ms": int, "window_title": str},
    "logging": {"level": str, "console": bool, "file": bool, "log_dir": str},
    "paths": {"captures": str, "exports": str, "logs": str},
}

THEME_NAMES = ("dark", "light")


def _user_config_dir() -> Path:
    override = os.environ.get(ENV_CONFIG_DIR)
    if override:
        return Path(override)
    if os.name == "nt":
        base = os.environ.get("APPDATA", str(Path.home() / "AppData" / "Roaming"))
        return Path(base) / USER_APP_NAME
    xdg = os.environ.get("XDG_CONFIG_HOME")
    base = Path(xdg) if xdg else Path.home() / ".config"
    return base / USER_APP_NAME


def bundled_config_path() -> Path:
    """config/default.json at the repository root."""
    return Path(__file__).resolve().parent.parent / "config" / "default.json"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigurationError(
            f"invalid JSON in {path}: {exc}", code="CONFIG_BAD_JSON"
        ) from exc
    if not isinstance(data, dict):
        raise ConfigurationError(
            f"config file {path} must contain a JSON object", code="CONFIG_BAD_JSON"
        )
    return data


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _validate(merged: dict[str, Any]) -> None:
    for section, keys in _SCHEMA.items():
        data = merged.get(section)
        if not isinstance(data, dict):
            raise ConfigurationError(
                f"config section '{section}' must be an object", code="CONFIG_BAD_SECTION"
            )
        for key, expected in keys.items():
            if key in data and not isinstance(data[key], expected):
                raise ConfigurationError(
                    f"config {section}.{key} must be of type {expected.__name__}",
                    code="CONFIG_BAD_TYPE",
                    context={"path": f"{section}.{key}"},
                )
    for section in merged:
        if section not in _SCHEMA and section != "app":
            log.warning("unknown config section '%s' (ignored)", section)


@dataclass
class AppConfig:
    """Validated, flat configuration view."""

    gui_theme: str
    ui_poll_ms: int
    window_title: str
    log_level: str
    log_console: bool
    log_file: bool
    log_dir: str
    captures_dir: str
    exports_dir: str
    config_dir: Path
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "gui_theme": self.gui_theme,
            "ui_poll_ms": self.ui_poll_ms,
            "window_title": self.window_title,
            "log_level": self.log_level,
            "log_dir": self.log_dir,
            "captures_dir": self.captures_dir,
            "exports_dir": self.exports_dir,
            "config_dir": str(self.config_dir),
        }


def load_config(
    path: str | Path | None = None,
    config_dir: Path | None = None,
) -> AppConfig:
    """Load and validate configuration (see module docstring for precedence)."""
    cfg_dir = Path(config_dir) if config_dir else _user_config_dir()
    merged = copy.deepcopy(_DEFAULTS)

    bundled = bundled_config_path()
    if bundled.exists():
        merged = _deep_merge(merged, _read_json(bundled))
    if path is not None:
        merged = _deep_merge(merged, _read_json(Path(path)))
    user_cfg = cfg_dir / "config.json"
    if user_cfg.exists():
        merged = _deep_merge(merged, _read_json(user_cfg))

    env_level = os.environ.get(ENV_LOG_LEVEL)
    if env_level:
        merged.setdefault("logging", {})["level"] = env_level.upper()

    _validate(merged)

    gui = merged["gui"]
    logsec = merged["logging"]
    paths = merged["paths"]
    if gui["theme"] not in THEME_NAMES:
        raise ConfigurationError(
            f"gui.theme must be one of {THEME_NAMES}", code="CONFIG_BAD_THEME"
        )
    if not 10 <= int(gui["ui_poll_ms"]) <= 1000:
        raise ConfigurationError(
            "gui.ui_poll_ms must be between 10 and 1000", code="CONFIG_BAD_POLL"
        )

    return AppConfig(
        gui_theme=str(gui["theme"]),
        ui_poll_ms=int(gui["ui_poll_ms"]),
        window_title=str(gui["window_title"]),
        log_level=str(logsec["level"]).upper(),
        log_console=bool(logsec["console"]),
        log_file=bool(logsec["file"]),
        log_dir=str(logsec["log_dir"]),
        captures_dir=str(paths["captures"]),
        exports_dir=str(paths["exports"]),
        config_dir=cfg_dir,
        raw=merged,
    )
