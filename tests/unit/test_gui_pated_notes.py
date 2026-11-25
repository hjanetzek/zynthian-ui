"""zyngui.zynthian_gui_pated_notes: grid touch/mouse handling (on a bare instance, no Tk widgets)."""

from types import SimpleNamespace

import pytest

from zyngui.zynthian_gui_pated_notes import zynthian_gui_pated_notes


def make_screen():
    screen = zynthian_gui_pated_notes.__new__(zynthian_gui_pated_notes)
    screen.grid_drag_start = SimpleNamespace(x=100, y=100, time=0)
    screen.grid_drag_count = 0
    screen.drag_note = False
    screen.step_width = 10
    screen.row_height = 10
    screen.step_offset = 5
    screen.keymap_offset = 0
    screen.view_rows = 8
    screen.selected_cell = [0, 0]
    screen.offsets = []
    screen.set_step_offset = screen.offsets.append
    screen.set_keymap_offset = lambda offset: None
    screen.select_cell = lambda *args: None
    return screen


def test_a_horizontal_drag_scrolls():
    screen = make_screen()
    screen.on_grid_drag(SimpleNamespace(x=60, y=100, time=100))
    assert screen.grid_drag_count == 1
    assert screen.offsets and screen.offsets[-1] > 5


@pytest.mark.parametrize("x, y", [(100, 100), (101, 101)])
def test_a_tap_isnt_a_drag(x, y):
    screen = make_screen()
    screen.on_grid_drag(SimpleNamespace(x=x, y=y, time=100))
    assert screen.grid_drag_count == 0


# --- Pattern options: recording from MIDI ----------------------------------------------------------------
class FakeLibseq:
    def __init__(self, record):
        self.record = record

    def isMidiRecord(self):
        return self.record

    def enableMidiRecord(self, on):
        self.record = on

    def __getattr__(self, name):
        return lambda *args: 0


def make_menu_screen(record):
    from zyngui.zynthian_gui_pated_base import zynthian_gui_pated_base
    screen = zynthian_gui_pated_base.__new__(zynthian_gui_pated_base)
    screen.seq_info = None
    screen.n_steps_beat = 4
    screen.get_pattern_length = lambda: "1 bar"
    screen.get_name = lambda: "pated note"
    screen.zynseq = SimpleNamespace(libseq=FakeLibseq(record))
    screen.zyngui = SimpleNamespace(multitouch=SimpleNamespace(_f_device=None))
    return screen


@pytest.mark.parametrize("record, label", [(False, "☐ Record from MIDI"), (True, "☒ Record from MIDI")])
def test_touch_navigation_menu_has_record_from_midi(monkeypatch, record, label):
    """Without a REC button in sight (the touch keypad is hidden by default) the menu toggles it."""
    from zyngui import zynthian_gui_config
    monkeypatch.setattr(zynthian_gui_config, "touch_navigation", "v5_keypad_left")
    options = make_menu_screen(record).get_menu_options()["EDIT"]
    assert options[label] == "Record MIDI"


def test_record_from_midi_not_in_the_menu_without_touch_navigation(monkeypatch):
    from zyngui import zynthian_gui_config
    monkeypatch.setattr(zynthian_gui_config, "touch_navigation", "")
    options = make_menu_screen(False).get_menu_options()["EDIT"]
    assert "Record MIDI" not in options.values()
