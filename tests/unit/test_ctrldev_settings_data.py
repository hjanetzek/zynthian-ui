"""The shared controller settings logic (zyngui.zynthian_ctrldev_settings_data): which drivers have
settings, the categories and settings shown (hidden and action settings left out), the values as
shown and as set."""

from tests.fakes.ctrldev_settings import JAM, PUSH2, FakeCtrldevManager, FakeSettingsDriver
from zyngui import zynthian_ctrldev_settings_data as data


class NoSettings:
    def get_driver_name(self):
        return "Plain driver"


def by_label(settings, label):
    return next(s for s in settings if s["label"] == label)


def test_drivers_with_settings():
    push, jam = FakeSettingsDriver("Push 2", PUSH2), FakeSettingsDriver("JAM", JAM)
    manager = FakeCtrldevManager([push, NoSettings()], [jam])
    assert data.settings_drivers(manager) == [push, jam]
    assert data.settings_drivers(None) == []
    assert data.driver_title(push) == "Push 2"
    assert data.driver_title(object()) == "object"


def test_categories_in_order_without_hidden_and_actions():
    push = FakeSettingsDriver("Push 2", PUSH2)
    settings = push.get_settings()
    cats = data.categories(settings)
    assert cats[:3] == ["Scales", "Note Repeat", "Session"]
    assert "Debug" not in cats   # only an action
    flexi = [data.label(s) for s in data.category_settings(settings, "Flexi")]
    assert flexi == ["Slot 1 Active"]   # the command is hidden while the slot is off
    push.set_setting(by_label(settings, "Slot 1 Active")["id"], "true")
    assert [data.label(s) for s in data.category_settings(push.get_settings(), "Flexi")] == \
        ["Slot 1 Active", "Slot 1 Command"]


def test_hidden_category_and_disabled():
    push = FakeSettingsDriver("Push 2", PUSH2)
    push.set_state("Sensitivity", visible=False)
    assert "Pads" not in data.categories(push.get_settings())
    push.set_state("Display Brightness", enabled=False)
    s = by_label(push.get_settings(), "Display Brightness")
    assert not data.is_enabled(s)
    assert "Not available" in data.info_text(s)


def test_values():
    settings = FakeSettingsDriver("Push 2", PUSH2).get_settings()
    accent = by_label(settings, "Fixed Accent Value")
    assert data.int_range(accent) == (1, 127)
    assert data.int_value(accent) == 127
    assert data.clamp_int(accent, 500) == 127 and data.clamp_int(accent, -3) == 1
    assert data.value_text(by_label(settings, "Slot 1 Active")) == "Off"
    assert data.value_text(by_label(settings, "Background")) == "#535353"
    assert data.signal_text(by_label(settings, "Reset colors to default")) == "Reset"
    assert data.enum_options(by_label(settings, "In Key")) == ["In Key", "Chromatic"]
    assert "Saved with the snapshot." in data.info_text(by_label(settings, "Scale"))
    assert "Kept by the controller." in data.info_text(by_label(settings, "Pads"))
    # Without min and max: 0..127, widened to hold the value
    assert data.int_range({"kind": "integer", "value": "300", "extra": []}) == (0, 300)
    assert data.int_value({"kind": "integer", "value": "x", "default": "7"}) == 7


def test_apply_as_the_core_takes_it():
    push = FakeSettingsDriver("Push 2", PUSH2)
    settings = push.get_settings()
    assert data.apply(push, by_label(settings, "Slot 1 Active"), True)
    assert data.apply(push, by_label(settings, "Fixed Accent Value"), 999)
    assert data.apply(push, by_label(settings, "Reset colors to default"), "anything")
    assert push.calls == [(by_label(settings, "Slot 1 Active")["id"], "true"),
                          (by_label(settings, "Fixed Accent Value")["id"], "127"),
                          (by_label(settings, "Reset colors to default")["id"], "")]
    push.running = False
    assert not data.apply(push, by_label(settings, "Scale"), "Minor")


def test_signal_without_label_shows_its_button_text():
    """A blank-label signal (Push's debug "Display window") shows its button text, as Bitwig"""
    assert data.label({"id": 7, "kind": "signal", "label": "", "extra": "Display window"}) == "Display window"
    assert data.label({"id": 7, "kind": "signal", "label": " ", "extra": ""}) == "Setting 7"
    assert data.label({"id": 8, "kind": "integer", "label": "", "extra": "0..10"}) == "Setting 8"
