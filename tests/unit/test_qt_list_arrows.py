"""ARROW_LEFT / ARROW_RIGHT in the Qt UI's lists (an experiment, navigation only; Tk's lists ignore
them): left goes one level back as switch 1 short, Tk's BACK on the kits (the screen's switch
first: the preset list -> the bank list); right enters the selected entry as SELECT short only
when it opens a level (a submenu, the presets of a bank, a folder: SelectorScreen.enters), else
nothing: it never loads a preset, runs an option or toggles a setting. For the V5 touch keypad
(the Lenovo Duet), which has no switch 1: its BACK key (the BACK CUIA) leaves the preset list as
in Tk. Grids move, category lists (the engine list) switch the category, as before.
docs/qt-navigation.md."""

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
def test_right_in_the_presets_does_nothing(app, flat):
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
    assert chosen == [] and ui.current_screen == "preset"
    ui._navigate("select")
    assert chosen == [(2, "S")]


def test_right_enters_a_preset_folder(app, tmp_path):
    ui = nav_ui(banks=3)
    preset = ui.list_screens["preset"]
    chosen = []
    preset.select_action = lambda index, t: chosen.append(index)
    preset.selection_changed = lambda: None
    folder = tmp_path / "Loops"
    folder.mkdir()
    preset.set_entries([entry("Loops", data=[str(folder), 0, "Loops"]),
                        entry("a.wav", data=[str(tmp_path / "a.wav"), 1, "a.wav"])], 0)
    ui.show_screen("chain_control")
    ui.show_screen("preset")
    ui._navigate("right")
    preset.set_index(1)
    ui._navigate("right")
    assert chosen == [0]


class Plain(SelectorScreen):
    name = "plain"

    def __init__(self, ui, kind="list"):
        super().__init__(ui)
        self.kind = kind
        self.chosen = []
        self.set_entries([entry(t, action=self.chosen.append, level=t in "bd") for t in "abcd"], 1)

    def fill(self):
        pass


def plain_ui(kind="list"):
    ui = nav_ui()
    screen = ui.list_screens["plain"] = Plain(ui, kind)
    ui.show_screen("chain_control")
    ui.show_screen("plain")
    return ui, screen


def test_left_in_a_plain_list_goes_back_right_enters_only_levels(app):
    ui, screen = plain_ui()
    ui._navigate("right")                        # b: a level
    assert [e["title"] for e in screen.chosen] == ["b"]
    screen.set_index(2)
    ui._navigate("right")                        # c: an action
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


def test_the_options_list_right_does_nothing(app):
    from zynqt.screens.snapshots import Options
    ui = nav_ui()
    ran = []
    options = ui.list_screens["option"] = Options(ui)
    options.fill = lambda: None
    options.set_entries([entry("Load", action=lambda e: ran.append("load"))], 0)
    ui.show_screen("chain_control")
    ui.show_screen("option")
    ui._navigate("right")
    assert ran == [] and ui.current_screen == "option"
    ui._navigate("left")
    assert ui.current_screen == "chain_control"


def test_snapshots_enter_banks_only(app, tmp_path):
    from zynqt.screens.snapshots import Snapshots
    (tmp_path / "000").mkdir()
    snap = tmp_path / "000" / "a.zss"
    snap.write_text("{}")
    s = Snapshots.__new__(Snapshots)
    SelectorScreen.__init__(s, SimpleNamespace(state_manager=SimpleNamespace(snapshot_dir=str(tmp_path)),
                                               chain_manager=None))
    rows = [[str(tmp_path), 0, ".."], [str(tmp_path / "000"), 1, "000"], [str(snap), 2, "a"],
            ["NEW_BANK", 3, "New Bank"]]
    s.set_entries([entry(r[2], data=r) for r in rows], 0)
    assert [s.enters(i) for i in range(4)] == [False, True, False, False]


def test_file_selector_enters_directories_only(app, tmp_path):
    from zynqt.screens.file_selector import FileSelector
    (tmp_path / "dir").mkdir()
    (tmp_path / "f.mid").write_text("")
    s = FileSelector.__new__(FileSelector)
    SelectorScreen.__init__(s, SimpleNamespace(state_manager=None, chain_manager=None))
    s.selection_changed = lambda: None   # the preview
    s.set_entries([entry("dir", data=str(tmp_path / "dir")), entry("f", data=str(tmp_path / "f.mid")),
                   entry("none", data=None)], 0)
    assert [s.enters(i) for i in range(3)] == [True, False, False]
