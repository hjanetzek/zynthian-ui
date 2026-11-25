"""The Qt UI's controller settings screen (zynqt.screens.controller_settings): drivers, categories
and settings as three levels with BACK, a widget per kind (options list, value editor, keyboard,
toggle, button), hidden settings left out and disabled ones greyed, and the refill when a driver's
settings_revision changes (polled while the screen is shown)."""

from types import SimpleNamespace

import pytest

QtCore = pytest.importorskip("PySide6.QtCore")
pytest.importorskip("zynqt.ui")

from tests.fakes.ctrldev_settings import JAM, PUSH2, FakeCtrldevManager, FakeSettingsDriver  # noqa: E402
from tests.unit.test_qt_gui_thread import app, wait_for  # noqa: E402,F401
from zynqt.screens import controller_settings as cs  # noqa: E402


class FakeUI:
    def __init__(self, manager):
        self.state_manager = SimpleNamespace(ctrldev_manager=manager)
        self.chain_manager = None
        self.options = None
        self.value_editor = None
        self.keyboard = None
        self.infos = []

    def show_options(self, title, options, selected=0):
        self.options = (title, options, selected)

    def edit_value(self, title, value, vmin, vmax, action, step=1, decimals=0):
        self.value_editor = (title, value, vmin, vmax, action)

    def show_keyboard(self, action, text="", title=""):
        self.keyboard = (title, text, action)

    def show_info(self, text, ms=2500):
        self.infos.append(text)


@pytest.fixture
def setup(app):
    push, jam = FakeSettingsDriver("DrivenByMoss Ableton Push 2", PUSH2), FakeSettingsDriver("DrivenByMoss JAM", JAM)
    manager = FakeCtrldevManager([push], [jam])
    ui = FakeUI(manager)
    screen = cs.ControllerSettings(ui)
    screen.build()
    yield SimpleNamespace(screen=screen, ui=ui, push=push, jam=jam, manager=manager)
    screen.hide()


def titles(screen):
    return [e["title"] for e in screen.entries]


def select(screen, title):
    i = next(i for i, t in enumerate(titles(screen)) if t == title or t.startswith(title + ":"))
    screen.activate(i, "S")


def test_levels_and_back(setup):
    s = setup.screen
    assert s.title == "Controller Settings"
    assert titles(s) == ["DrivenByMoss Ableton Push 2", "DrivenByMoss JAM"]
    select(s, "DrivenByMoss Ableton Push 2")
    assert s.title == "DrivenByMoss Ableton Push 2"
    assert titles(s)[:3] == ["Scales", "Note Repeat", "Session"]
    assert "Debug" not in titles(s)   # only an action setting
    select(s, "Workflow")
    assert s.title == "Workflow"
    assert titles(s) == ["Exclude deactivated items (tracks, sends, devices, layers): Off", "New Clip Length: 1 Bar"]
    assert s.back()
    assert titles(s)[s.index] == "Workflow"
    assert s.back()
    assert titles(s)[s.index] == "DrivenByMoss Ableton Push 2"
    assert not s.back()


def test_widgets(setup):
    s, ui, push = setup.screen, setup.ui, setup.push
    select(s, "DrivenByMoss Ableton Push 2")
    select(s, "Workflow")
    # enum: the options list, the current one checked and selected
    select(s, "New Clip Length")
    title, options, selected = ui.options
    assert title == "New Clip Length" and options[selected][0] == "☒ 1 Bar"
    next(action for label, action, _, _ in options if label.endswith("4 Bars"))()
    assert "New Clip Length: 4 Bars" in titles(s)
    s.back()
    # integer: the value editor with min and max
    select(s, "Hardware Setup")
    select(s, "Display Brightness")
    title, value, vmin, vmax, action = ui.value_editor
    assert (title, value, vmin, vmax) == ("Display Brightness", 100, 0, 100)
    action(42)
    assert titles(s) == ["Display Brightness: 42"]
    s.back()
    # text: the keyboard; signal: a button, at once
    select(s, "Display Colors")
    assert titles(s)[0] == "▶ Reset colors to default"
    assert s.entries[0]["info"].startswith("Press to reset.")
    select(s, "Background")
    title, text, action = ui.keyboard
    assert (title, text) == ("Background", "#535353")
    action("#102030")
    assert "Background: #102030" in titles(s)
    s.activate(0, "S")
    assert "Background: #535353" in titles(s), "The reset restored the colours"
    s.back()
    # boolean: toggles; the Flexi slot's command appears when it is on (the controller's state)
    select(s, "Flexi")
    assert titles(s) == ["☐ Slot 1 Active"]
    s.activate(0, "S")
    assert titles(s) == ["☒ Slot 1 Active", "Slot 1 Command: Off"]
    assert push.calls[-1] == (next(x["id"] for x in push.settings if x["label"] == "Slot 1 Active"), "true")


def test_disabled_is_greyed_and_not_changed(setup):
    s, ui, push = setup.screen, setup.ui, setup.push
    push.set_state("Display Brightness", enabled=False)
    select(s, "DrivenByMoss Ableton Push 2")
    select(s, "Hardware Setup")
    assert not s.entries[0]["enabled"]
    calls = len(push.calls)
    s.activate(0, "S")
    assert ui.value_editor is None and len(push.calls) == calls
    assert "Not available" in ui.infos[-1]


def test_polling_refills(setup, app):
    s, push = setup.screen, setup.push
    select(s, "DrivenByMoss Ableton Push 2")
    select(s, "Scales")
    assert titles(s)[0] == "Scale: Major"
    push.controller_changes("Scale", "Dorian")   # chosen on the controller
    assert wait_for(app, lambda: titles(s)[0] == "Scale: Dorian")
    push.set_state("Base", visible=False)
    assert wait_for(app, lambda: "Base: C" not in titles(s))
    # The whole category hidden: back to the categories
    for label in ("Scale", "In Key"):
        push.set_state(label, visible=False)
    assert wait_for(app, lambda: s.title == "DrivenByMoss Ableton Push 2")
    # The controller stops (asleep): back to the drivers, its entry greyed; unplugged (driver
    # unloaded): gone
    push.running = False
    push.settings_revision += 1
    assert wait_for(app, lambda: s.title == "Controller Settings")
    assert [e["enabled"] for e in s.entries] == [False, True]
    del setup.manager.drivers[0]
    assert wait_for(app, lambda: titles(s) == ["DrivenByMoss JAM"])


def test_not_running_and_none(app):
    push = FakeSettingsDriver("Push 2", PUSH2, running=False)
    screen = cs.ControllerSettings(FakeUI(FakeCtrldevManager([push])))
    screen.build()
    screen.hide()
    assert not screen.entries[0]["enabled"]
    assert "isn't running" in screen.entries[0]["info"]
    screen = cs.ControllerSettings(FakeUI(FakeCtrldevManager()))
    screen.build()
    screen.hide()
    assert titles(screen) == ["No controller with settings"]
