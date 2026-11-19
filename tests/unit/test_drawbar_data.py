"""Drawbar widget logic (zyngui.zynthian_widget_data drawbar_*, shared by the Tk drawbar / setBfree
widgets and the Qt drawbar view; upstream PR 612)."""

from types import SimpleNamespace

import pytest

wd = pytest.importorskip("zyngui.zynthian_widget_data")

SETBFREE_TICKS = [127, 119, 103, 87, 71, 55, 39, 23, 7]


class Ctrl:
    def __init__(self, ticks=None, vmin=0.0, vmax=8.0, value=0.0, drawbar=False):
        self.ticks, self.value_min, self.value_max, self.value = ticks, vmin, vmax, value
        if drawbar:
            self.drawbar = True

    def set_value(self, v):
        self.value = v


def test_setbfree_ticks_are_knots():
    c = Ctrl(SETBFREE_TICKS)
    assert wd.drawbar_position(c, 127) == 0.0
    assert wd.drawbar_position(c, 7) == 8.0
    assert wd.drawbar_position(c, 95) == pytest.approx(2.5)
    assert wd.drawbar_value(c, 2.5) == pytest.approx(95)
    # beyond the ends
    assert wd.drawbar_position(c, 0) == 8.0
    assert wd.drawbar_value(c, 12) == 7


def test_linear_controller():
    c = Ctrl(vmin=0.0, vmax=8.0)
    assert wd.drawbar_position(c, 3.0) == 3.0
    assert wd.drawbar_value(c, -1) == 0.0


def test_drag_from_the_press_value():
    c = Ctrl(SETBFREE_TICKS, value=127)
    wd.drawbar_drag(c, 127, 0.5)        # half the height down: pulled out to 4
    assert c.value == pytest.approx(71)
    wd.drawbar_drag(c, 127, -0.5)       # up from pushed in: stays in
    assert c.value == 127


def test_symbols():
    proc = SimpleNamespace(controllers_dict={"a": Ctrl(drawbar=True), "b": Ctrl(), "c": Ctrl(drawbar=True)})
    assert wd.drawbar_symbols(proc) == ["a", "c"]
    assert wd.drawbar_symbols(None, setbfree=True)[0] == "DB 16"
    assert len(wd.DRAWBARS) == wd.DRAWBAR_SLOTS == len(wd.SETBFREE_DRAWBARS)


def test_setbfree_is_a_plugin_widget():
    proc = SimpleNamespace(engine=SimpleNamespace(custom_gui_fpath="/x/zyngui/zynthian_widget_setbfree.py"))
    assert wd.plugin_widget(proc) == "setbfree"
