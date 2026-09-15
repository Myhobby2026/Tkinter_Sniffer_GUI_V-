import logging

from app.logging_setup import (
    TRACE,
    LOG_FILE_NAME,
    LogNames,
    LoggingConfig,
    export_logs,
    flush_all,
    make_logger,
    setup_logging,
    trace,
)


def test_trace_level_registered():
    assert logging.getLevelName(TRACE) == "TRACE"


def test_setup_creates_file_and_records(tmp_path):
    setup_logging(LoggingConfig(level="TRACE", console=False, file=True, log_dir=tmp_path))
    log = make_logger(LogNames.CAPTURE)
    log.info("capture started")
    trace(log, "trace line %d", 1)
    flush_all()
    content = (tmp_path / LOG_FILE_NAME).read_text(encoding="utf-8")
    assert "capture started" in content
    assert "TRACE" in content and "trace line 1" in content


def test_setup_idempotent(tmp_path):
    setup_logging(LoggingConfig(level="DEBUG", console=False, file=True, log_dir=tmp_path))
    setup_logging(LoggingConfig(level="DEBUG", console=False, file=True, log_dir=tmp_path))
    root = logging.getLogger(LogNames.ROOT)
    assert len(root.handlers) == 1  # not double-added


def test_export_logs(tmp_path):
    src = tmp_path / "logs"
    setup_logging(LoggingConfig(level="DEBUG", console=False, file=True, log_dir=src))
    make_logger(LogNames.APP).info("diag data")
    flush_all()
    dest = tmp_path / "bundle"
    written = export_logs(dest, src)
    assert len(written) == 1
    assert written[0].exists()
    assert "diag data" in written[0].read_text(encoding="utf-8")


def test_namespaced_loggers_exist():
    for name in LogNames.ALL:
        logger = make_logger(name)
        assert logger.name == name
        assert logger.name.startswith(LogNames.ROOT)
