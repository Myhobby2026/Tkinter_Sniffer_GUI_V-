import json

import pytest

from app.config import ENV_CONFIG_DIR, ENV_LOG_LEVEL, load_config
from app.errors import ConfigurationError


@pytest.fixture
def isolated_config(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_CONFIG_DIR, str(tmp_path))
    monkeypatch.delenv(ENV_LOG_LEVEL, raising=False)
    return tmp_path


def test_defaults(isolated_config):
    cfg = load_config()
    assert cfg.gui_theme == "dark"
    assert cfg.ui_poll_ms == 50
    assert cfg.log_level == "INFO"
    assert cfg.captures_dir == "captures"
    assert str(cfg.config_dir) == str(isolated_config)


def test_user_override(isolated_config):
    (isolated_config / "config.json").write_text(
        json.dumps({"gui": {"theme": "light"}, "logging": {"level": "debug"}}),
        encoding="utf-8",
    )
    cfg = load_config()
    assert cfg.gui_theme == "light"
    assert cfg.log_level == "DEBUG"
    # untouched values keep defaults
    assert cfg.ui_poll_ms == 50


def test_explicit_path(tmp_path, monkeypatch):
    monkeypatch.setenv(ENV_CONFIG_DIR, str(tmp_path / "unused"))
    explicit = tmp_path / "explicit.json"
    explicit.write_text(json.dumps({"paths": {"captures": "mycaps"}}), encoding="utf-8")
    cfg = load_config(explicit)
    assert cfg.captures_dir == "mycaps"


def test_bad_type_rejected(isolated_config):
    (isolated_config / "config.json").write_text(
        json.dumps({"gui": {"ui_poll_ms": "fast"}}), encoding="utf-8"
    )
    with pytest.raises(ConfigurationError) as excinfo:
        load_config()
    assert excinfo.value.code == "CONFIG_BAD_TYPE"


def test_bad_theme_rejected(isolated_config):
    (isolated_config / "config.json").write_text(
        json.dumps({"gui": {"theme": "neon"}}), encoding="utf-8"
    )
    with pytest.raises(ConfigurationError) as excinfo:
        load_config()
    assert excinfo.value.code == "CONFIG_BAD_THEME"


def test_bad_json_rejected(isolated_config):
    (isolated_config / "config.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(ConfigurationError) as excinfo:
        load_config()
    assert excinfo.value.code == "CONFIG_BAD_JSON"


def test_unknown_section_ignored(isolated_config):
    (isolated_config / "config.json").write_text(
        json.dumps({"future_feature": {"x": 1}}), encoding="utf-8"
    )
    cfg = load_config()  # must not raise
    assert cfg.gui_theme == "dark"


def test_env_log_level(isolated_config, monkeypatch):
    monkeypatch.setenv(ENV_LOG_LEVEL, "debug")
    cfg = load_config()
    assert cfg.log_level == "DEBUG"
