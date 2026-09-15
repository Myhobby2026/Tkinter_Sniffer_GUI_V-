import pytest

from app.core.sample_block import CaptureBlock
from app.errors import USBError
from app.transport import (
    Transport,
    TransportEvent,
    TransportEventKind,
    TransportManager,
    TransportRegistry,
    TransportState,
)


class FakeTransport(Transport):
    def __init__(self, name="fake") -> None:
        super().__init__(name)
        self.commands: list[bytes] = []
        self.opened = False

    def open(self, options=None) -> None:
        self.opened = True
        self._state = TransportState.OPEN
        self.post_event(TransportEvent(TransportEventKind.DEVICE_STATUS,
                                       {"state": "connected"}))

    def close(self) -> None:
        self._state = TransportState.CLOSED
        self.post_event(TransportEvent(TransportEventKind.CLOSED))

    def send_command(self, command: bytes) -> None:
        self.commands.append(command)


def test_registry_register_create():
    reg = TransportRegistry()
    reg.register("fake", FakeTransport)
    assert reg.kinds() == ["fake"]
    transport = reg.create("fake")
    assert isinstance(transport, FakeTransport)
    with pytest.raises(USBError) as excinfo:
        reg.create("missing")
    assert excinfo.value.code == "TRANSPORT_UNKNOWN"
    with pytest.raises(USBError):
        reg.register("fake", FakeTransport)  # duplicate


def test_manager_open_close_flow():
    tm = TransportManager(TransportRegistry())
    tm.registry.register("fake", FakeTransport)
    assert "fake" in tm.available()
    transport = tm.open("fake")
    assert transport.state is TransportState.OPEN
    transport.send_command(b"\x01\x02")
    events = transport.drain_events()
    assert events[0].kind is TransportEventKind.DEVICE_STATUS
    assert events[0].data == {"state": "connected"}
    tm.close(transport)
    assert transport.state is TransportState.CLOSED
    assert transport.commands == [b"\x01\x02"]


def test_drain_is_nonblocking_and_bounded():
    transport = FakeTransport()
    for i in range(10):
        transport.post_event(TransportEvent(TransportEventKind.BLOCK, i))
    first = transport.drain_events(max_events=4)
    assert [e.data for e in first] == list(range(4))
    assert all(e.kind is TransportEventKind.BLOCK for e in first)
    assert len(transport.drain_events()) == 6
    assert transport.drain_events() == []


def test_usb_transport_stub_fails_fast():
    from app.transport.usb_transport import USBTransport

    transport = USBTransport()
    with pytest.raises(USBError) as excinfo:
        transport.open()
    assert "Phase 3" in str(excinfo.value)


def test_block_event_carrying_blocks():
    """Transport events carry CaptureBlocks (the Phase 3 contract)."""
    transport = FakeTransport()
    block = CaptureBlock(seq=0, sample_index=0, device_ts_us=0, channel_mask=0xF,
                         sample_count=1, payload=b"\x00")
    transport.post_event(TransportEvent(TransportEventKind.BLOCK, block))
    [event] = transport.drain_events()
    assert event.data.seq == 0
