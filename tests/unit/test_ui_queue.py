import time

from app.gui.commands import Cmd, Command
from app.gui.ui_queue import EVENT_CAPTURE, EVENT_DEVICE, EVENT_ERROR, UiEventQueue


def test_post_drain_order():
    q = UiEventQueue()
    q.post("status", a=1)
    q.post("message", text="hi")
    events = q.drain()
    assert [(e.kind, e.data) for e in events] == [
        ("status", {"a": 1}),
        ("message", {"text": "hi"}),
    ]
    assert q.drain() == []


def test_clear():
    q = UiEventQueue()
    for i in range(3):
        q.post("x", i=i)
    assert q.clear() == 3
    assert q.drain() == []
    assert q.pending_count() == 0


def test_threaded_posts_are_not_lost():
    q = UiEventQueue()
    n = 2000

    def producer():
        for i in range(n):
            q.post("data", i=i)

    threads = [__import__("threading").Thread(target=producer) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    events = q.drain()
    assert len(events) == 4 * n
    assert q.pending_count() == 0


def test_drain_does_not_block():
    q = UiEventQueue()
    start = time.monotonic()
    assert q.drain() == []
    assert time.monotonic() - start < 0.05
