import pytest

from app.errors import DecoderError
from app.protocol import (
    DECODER_API_VERSION,
    DecodedEvent,
    DecoderInfo,
    DecoderStatus,
    ProtocolDecoder,
    api_version_compatible,
)
from app.protocol.decoder_registry import DecoderRegistry
from tests.conftest import make_batch


class EchoDecoder(ProtocolDecoder):
    """Tiny reference decoder used to pin down the API contract."""

    def __init__(self) -> None:
        self._info = DecoderInfo(
            id="echo",
            name="Echo",
            api_version=DECODER_API_VERSION,
            version="0.1.0",
            description="test decoder",
            required_channels=("CH0",),
            config_defaults={"channel_map": {"CH0": 0}},
        )
        self.calls = 0
        self.config: dict = {}

    @property
    def info(self) -> DecoderInfo:
        return self._info

    def configure(self, config: dict) -> None:
        self.config = dict(config)

    def reset(self) -> None:
        self.calls = 0

    def process(self, batch):
        self.calls += 1
        return [
            DecodedEvent(
                protocol="echo",
                event_type="batch",
                start_index=batch.start_index,
                duration=batch.n_samples,
                channel="CH0",
                fields={"n": batch.n_samples},
                text=f"{batch.n_samples} samples",
                status=DecoderStatus.OK,
            )
        ]

    def flush(self):
        return [DecodedEvent(protocol="echo", event_type="flush",
                             start_index=0, text="flush")]


def test_decoder_contract():
    decoder = EchoDecoder()
    decoder.configure({"channel_map": {"CH0": 0}})
    batch = make_batch(n_samples=32, n_channels=4)
    events = decoder.process(batch)
    assert len(events) == 1
    event = events[0]
    assert event.protocol == "echo"
    assert event.start_index == 0
    assert event.duration == 32
    assert event.status is DecoderStatus.OK
    flushed = decoder.flush()
    assert flushed[0].event_type == "flush"
    decoder.reset()
    assert decoder.calls == 0


def test_decoded_event_to_dict():
    event = DecodedEvent(protocol="spi", event_type="tx_word", start_index=10,
                         duration=8, payload=b"\x9f\xef", text="0x9FEF")
    d = event.to_dict()
    assert d["payload"] == "9fef"
    assert d["status"] == "ok"
    assert d["errors"] == []


def test_registry_register_list_create():
    reg = DecoderRegistry()
    reg.register(EchoDecoder)
    infos = reg.list_info()
    assert [i.id for i in infos] == ["echo"]
    assert infos[0].name == "Echo"
    fresh = reg.create("echo")
    assert isinstance(fresh, EchoDecoder)
    assert fresh is not None and fresh.calls == 0


def test_registry_duplicate_and_unknown():
    reg = DecoderRegistry()
    reg.register(EchoDecoder)
    with pytest.raises(DecoderError) as excinfo:
        reg.register(EchoDecoder)
    assert excinfo.value.code == "REGISTRY_DUP"
    with pytest.raises(DecoderError) as excinfo:
        reg.create("nope")
    assert excinfo.value.code == "REGISTRY_UNKNOWN"


def test_registry_rejects_incompatible_api():
    class FutureDecoder(EchoDecoder):
        def __init__(self) -> None:
            super().__init__()
            self._info = DecoderInfo(
                id="future", name="Future", api_version="2.0", version="0.1",
            )

    reg = DecoderRegistry()
    with pytest.raises(DecoderError) as excinfo:
        reg.register(FutureDecoder)
    assert excinfo.value.code == "REGISTRY_API_MISMATCH"


def test_registry_rejects_non_decoder():
    with pytest.raises(DecoderError):
        DecoderRegistry().register(dict)  # type: ignore[arg-type]


def test_api_version_compatibility():
    assert api_version_compatible("1.0", "1.3")
    assert not api_version_compatible("1.0", "2.0")
    assert not api_version_compatible("garbage", "1.0")


def test_default_registry_is_singleton():
    from app.protocol import default_registry

    assert default_registry() is default_registry()
