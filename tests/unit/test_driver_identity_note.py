"""The controller driver list's SysEx identity note (upstream 07793ae7): driver_description() adds
it for drivers matching the device's identity, and the Qt UI's device options pass the state
manager and the device so the note shows there as in the Tk UI."""

import ast
import pathlib
from types import SimpleNamespace

import pytest

from zyngui.zynthian_midi_config_data import driver_description

pytestmark = pytest.mark.unit


class FakeDriver:
    @staticmethod
    def get_driver_description():
        return "Foot controller."


class OtherDriver:
    @staticmethod
    def get_driver_description():
        return None


def fake_sm(matching, identity="Behringer FCB1010"):
    cdm = SimpleNamespace(get_identity_drivers=lambda idev: matching if idev == 3 else [],
                          get_identity_str=lambda idev: identity)
    return SimpleNamespace(ctrldev_manager=cdm)


def test_note_for_a_driver_matching_the_identity():
    text = driver_description(FakeDriver, fake_sm([FakeDriver]), 3)
    assert text.startswith("Foot controller.")
    assert "Matches the device's SysEx identity (Behringer FCB1010)." in text


def test_no_note_for_other_drivers_devices_or_without_state_manager():
    assert "SysEx identity" not in driver_description(OtherDriver, fake_sm([FakeDriver]), 3)
    assert "SysEx identity" not in driver_description(FakeDriver, fake_sm([FakeDriver]), 4)
    assert driver_description(FakeDriver) == "Foot controller."


def test_qt_device_options_pass_state_manager_and_device():
    src = pathlib.Path(__file__).resolve().parents[2] / "zynqt" / "screens" / "routing.py"
    calls = [n for n in ast.walk(ast.parse(src.read_text()))
             if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "driver_description"]
    assert calls, "the Qt device options don't list driver descriptions any more"
    for call in calls:
        assert len(call.args) == 3, "driver_description() needs (driver_class, state_manager, idev) for the note"
