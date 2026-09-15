from tests.conftest import make_block


def _feed(tracker, blocks):
    for block in blocks:
        tracker.feed(block)


def test_clean_capture_reports_ok():
    from app.core.integrity import IntegrityTracker

    tracker = IntegrityTracker()
    _feed(tracker, [make_block(seq=i) for i in range(5)])
    report = tracker.report()
    assert report.ok
    assert report.summary == "OK"
    assert report.blocks_received == 5
    assert report.last_seq == 4


def test_missing_blocks_detected():
    from app.core.integrity import IntegrityTracker

    tracker = IntegrityTracker()
    _feed(tracker, [make_block(seq=0), make_block(seq=2), make_block(seq=5)])
    report = tracker.report()
    assert not report.ok
    assert report.missing_blocks == 3  # seq 1, and seq 3+4
    assert report.summary == "WARNING: 3 blocks missing"


def test_crc_and_overflow_and_dedupe():
    from app.core.integrity import IntegrityTracker

    tracker = IntegrityTracker()
    _feed(tracker, [
        make_block(seq=0),
        make_block(seq=1, crc_ok=False),
        make_block(seq=2, crc_ok=False),
        make_block(seq=3, overflow=True),
        make_block(seq=3),  # duplicate
    ])
    report = tracker.report()
    assert report.crc_errors == 2
    assert report.overflow_blocks == 1
    assert report.duplicate_blocks == 1
    assert report.summary == (
        "WARNING: 2 CRC errors, 1 buffer overflow, 1 duplicate block"
    )


def test_spec_example_format():
    """Spec §12 example: 'WARNING: 37 blocks missing, 2 CRC errors, 1 buffer overflow'.

    seq 0 then seq 38 → missing are seq 1..37 (37 blocks).
    """
    from app.core.integrity import IntegrityTracker

    tracker = IntegrityTracker()
    _feed(tracker, [make_block(seq=0)] + [make_block(seq=38)] +
          [make_block(seq=39, crc_ok=False)] + [make_block(seq=40, crc_ok=False)] +
          [make_block(seq=41, overflow=True)])
    report = tracker.report()
    assert report.missing_blocks == 37
    assert report.summary == "WARNING: 37 blocks missing, 2 CRC errors, 1 buffer overflow"


def test_reset():
    from app.core.integrity import IntegrityTracker

    tracker = IntegrityTracker()
    _feed(tracker, [make_block(seq=0), make_block(seq=5)])
    tracker.reset()
    assert tracker.report().ok
    _feed(tracker, [make_block(seq=0), make_block(seq=1)])
    assert tracker.report().ok
