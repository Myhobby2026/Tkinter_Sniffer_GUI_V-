from app.errors import (
    ConfigurationError,
    CrcError,
    DeviceError,
    ErrorCategory,
    PluginError,
    SequenceGapError,
    SnifferError,
    USBError,
)


def test_all_categories_present():
    expected = {
        "DEVICE_ERROR", "USB_ERROR", "CAPTURE_ERROR", "BUFFER_OVERFLOW",
        "CRC_ERROR", "SEQUENCE_GAP", "DECODER_ERROR", "PROTOCOL_ERROR",
        "FILE_ERROR", "PLUGIN_ERROR", "SCRIPT_ERROR", "CONFIGURATION_ERROR",
    }
    assert {c.value for c in ErrorCategory} == expected


def test_error_attributes():
    err = DeviceError("boom", code="DEV_X", context={"port": "COM3"})
    assert err.message == "boom"
    assert err.code == "DEV_X"
    assert err.context == {"port": "COM3"}
    assert err.category is ErrorCategory.DEVICE


def test_to_dict_json_safe():
    d = SequenceGapError("gap", code="GAP", context={"seq": 42}).to_dict()
    assert d == {
        "category": "SEQUENCE_GAP",
        "code": "GAP",
        "message": "gap",
        "context": {"seq": 42},
    }


def test_subclass_categories():
    assert USBError("x").category is ErrorCategory.USB
    assert CrcError("x").category is ErrorCategory.CRC
    assert PluginError("x").category is ErrorCategory.PLUGIN
    assert ConfigurationError("x").category is ErrorCategory.CONFIGURATION
    assert isinstance(SnifferError("x"), Exception)
