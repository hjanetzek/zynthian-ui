"""ARROW_LEFT / ARROW_RIGHT in the Qt UI's lists (a deliberate deviation from Tk, whose lists ignore
them): left goes one level back as switch 1 short (the screen's switch first: the preset list ->
the bank list), right enters the selected entry as SELECT short. For the V5 touch keypad (the
Lenovo Duet), which has no switch 1: its BACK key (the BACK CUIA) leaves the preset list as in Tk,
so the bank list was out of reach. Grids move, category lists (the engine list) switch the
category, as before. docs/qt-navigation.md."""

from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6.QtCore")
ui_mod = pytest.importorskip("zynqt.ui")

from tests.unit.test_qt_gui_thread import app  # noqa: E402,F401
from tests.unit.test_qt_preset_back_to_banks import preset_ui  # noqa: E402
from zynqt.screens.base import SelectorScreen, entry, separator  # noqa: E402
from zynqt.screens.chain_screens import Bank  # noqa: E402

ZynUI = ui_mod.ZynUI


def nav_ui(banks=3, flat=False):
    ui = preset_ui(banks, flat)
    ui._navigate = ZynUI._navigate.__get__(ui)
    ui.showScreen = ui.show_screen
    bank = ui.list_screens["bank"] = Bank(ui)
    bank.fill = lambda: None
    return ui


@pytest.mark.parametrize("flat", [False, True])
def test_left_in_the_presets_shows_the_banks_then_goes_back(app, flat):
    ui = nav_ui(banks=3, flat=flat)
    ui.show_screen("chain_control")
    ui.show_screen("preset")
    ui._navigate("left")
    assert ui.current_screen == "bank"
    assert ui.screen_history == ["mixer", "chain_control"]
    ui._navigate("left")
    assert ui.current_screen == "chain_control"


def test_left_in_the_presets_with_one_bank_goes_back(app):
    ui = nav_ui(banks=1)
    ui.show_screen("chain_control")
    ui.show_screen("preset")
    ui._navigate("left")
    assert ui.current_screen == "chain_control"


def test_left_in_a_flat_list_no_longer_jumps_groups(app):
    ui = nav_ui(banks=3, flat=True)
    preset = ui.list_screens["preset"]
    jumps = []
    preset.move_group = jumps.append
    ui.show_screen("chain_control")
    ui.show_screen("preset")
    ui._navigate("left")
    assert jumps == [] and ui.current_screen == "bank"
    # The group knob still jumps
    assert preset.zynpot(1, 1) and jumps == [1]


def bank_proc(ui):
    p = ui.current_processor
    p.preset_list = []
    p.chosen = []

    def set_bank(i):
        p.chosen.append(i)
        return True

    def load():
        p.preset_list = [["p0", 0, "Preset 0"]]
    p.set_bank, p.set_show_fav_presets, p.load_preset_list = set_bank, lambda v: None, load
    return p


def test_right_in_the_banks_shows_the_presets(app):
    ui = nav_ui(banks=3)
    bank = ui.list_screens["bank"]
    p = bank_proc(ui)
    bank.set_entries([entry(f"Bank {i}", data=[f"b{i}", i, f"Bank {i}"]) for i in range(3)], 1)
    ui.show_screen("chain_control")
    ui.show_screen("bank")
    ui._navigate("right")
    assert p.chosen == [1]
    assert ui.current_screen == "preset"
    assert ui.screen_history == ["mixer", "chain_control", "bank"]


@pytest.mark.parametrize("flat", [False, True])
def test_right_in_the_presets_selects_as_select(app, flat):
    ui = nav_ui(banks=3, flat=flat)
    preset = ui.list_screens["preset"]
    chosen = []
    preset.select_action = lambda index, t: chosen.append((index, t))
    bank0 = ["b0", 0, "Bank 0"]
    rows = [[f"p{i}", i, t] for i, t in enumerate("ab")]
    if flat:
        rows = [(bank0, r) for r in rows]
    preset.selection_changed = lambda: None   # the info pane (the processor's paths)
    preset.set_entries([separator("Bank 0")] + [entry(t, data=r) for t, r in zip("ab", rows)], 2)
    ui.show_screen("chain_control")
    ui.show_screen("preset")
    ui._navigate("right")
    assert chosen == [(2, "S")]


class Plain(SelectorScreen):
    name = "plain"

    def __init__(self, ui, kind="list"):
        super().__init__(ui)
        self.kind = kind
        self.chosen = []
        self.set_entries([entry(t, action=self.chosen.append) for t in "abcd"], 1)

    def fill(self):
        pass


def plain_ui(kind="list"):
    ui = nav_ui()
    screen = ui.list_screens["plain"] = Plain(ui, kind)
    ui.show_screen("chain_control")
    ui.show_screen("plain")
    return ui, screen


def test_left_in_a_plain_list_goes_back_right_selects(app):
    ui, screen = plain_ui()
    ui._navigate("right")
    assert [e["title"] for e in screen.chosen] == ["b"]
    ui._navigate("left")
    assert ui.current_screen == "chain_control"


def test_left_in_a_list_runs_the_screens_back_first(app):
    ui, screen = plain_ui()
    steps = []
    screen.back = lambda: steps.append("back") or len(steps) == 1   # a sub-folder first
    ui._navigate("left")
    assert ui.current_screen == "plain"
    ui._navigate("left")
    assert ui.current_screen == "chain_control" and steps == ["back", "back"]


def test_the_grid_moves(app):
    ui, screen = plain_ui("grid")
    ui._navigate("right")
    assert screen._index == 2 and screen.chosen == []
    ui._navigate("left")
    ui._navigate("left")
    assert screen._index == 0 and ui.current_screen == "plain"


def test_a_category_list_switches_categories(app):
    ui, screen = plain_ui()
    switched = []
    screen.category_changed = lambda: switched.append(screen.categoryIndex)
    screen.set_categories(["Synth", "Sampler", "Other"], 1)
    ui._navigate("right")
    ui._navigate("left")
    ui._navigate("left")
    assert switched == [2, 1, 0]
    assert ui.current_screen == "plain" and screen.chosen == []


def test_the_value_editor_takes_the_arrows(app):
    ui, screen = plain_ui()
    steps = []
    ui._value_editor = True
    ui.valueEditorStep = steps.append
    ui._navigate("left")
    ui._navigate("right")
    assert steps == [-1, 1] and ui.current_screen == "plain" and screen.chosen == []
