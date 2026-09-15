import pytest

from app.errors import DeviceError
from app.hal.device import DeviceInfo, DeviceState
from app.hal.device_manager import DeviceManager
from app.hal.simulator import SimulatorDevice


def _dm_with_sim():
    dm = DeviceManager()
    dm.register(SimulatorDevice())
    return dm


def test_register_list_get():
    dm = _dm_with_sim()
    infos = dm.list_devices()
    assert len(infos) == 1
    assert infos[0].id == "simulator-0001"
    assert isinstance(dm.get("simulator-0001"), SimulatorDevice)


def test_duplicate_register_rejected():
    dm = _dm_with_sim()
    with pytest.raises(DeviceError) as excinfo:
        dm.register(SimulatorDevice())
    assert excinfo.value.code == "DEVICE_DUP"


def test_unknown_device():
    dm = DeviceManager()
    with pytest.raises(DeviceError) as excinfo:
        dm.get("nope")
    assert excinfo.value.code == "DEVICE_NOT_FOUND"


def test_connect_disconnect_states():
    dm = _dm_with_sim()
    device = dm.connect("simulator-0001")
    assert device.state is DeviceState.CONNECTED
    events = []
    dm.on_state_change(lambda dev, state: events.append((dev, state)))
    dm.disconnect("simulator-0001")
    assert device.state is DeviceState.DISCONNECTED
    assert events == [("simulator-0001", "disconnected")]


def test_devices_returns_info_and_state():
    dm = _dm_with_sim()
    dm.connect("simulator-0001")
    pairs = dm.devices()
    assert pairs[0][1] is DeviceState.CONNECTED
    assert isinstance(pairs[0][0], DeviceInfo)


def test_unregister():
    dm = _dm_with_sim()
    dm.unregister("simulator-0001")
    assert dm.list_devices() == []
