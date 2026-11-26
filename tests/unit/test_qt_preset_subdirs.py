"""The bank and preset lists' sub-folders (the audio player's folders, FluidSynth's bank
directories), as Tk: BANK_PRESET goes up one folder (zynthian_gui_bank / zynthian_gui_preset.
browse_back: the parent's info [3], the folder left selected [1]); BACK leaves the list (Tk's bank
and preset screens have no back_action); switch 1 short in the presets shows the banks (more than
one bank: zynthian_gui_preset.switch), in the banks it goes back. ARROW_LEFT (the Qt experiment)
goes up one folder, else as switch 1 short."""

from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6.QtCore")

from tests.unit.test_qt_gui_thread import app  # noqa: E402,F401
from zynqt.screens.base import entry  # noqa: E402
from zynqt.screens.chain_screens import Bank, Preset  # noqa: E402
from tests.unit.test_qt_list_arrows import nav_ui  # noqa: E402
from tests.unit.test_qt_custom_switch_screen import CTRL, switch_ui  # noqa: E402


def subdir(path, index, parent):
    """A processor's sub-folder info: [path, the folder's index in the parent, title, parent]"""
    return [path, index, f"> {path}", parent]


def screen(cls, attr):
    proc = SimpleNamespace(bank_subdir_info=None, preset_subdir_info=None)
    ui = SimpleNamespace(current_processor=proc, state_manager=None, chain_manager=None)
    s = cls(ui)
    s.fills = []

    def fill(keep=False):
        s.fills.append(getattr(proc, attr))
        s.set_entries([entry(f"e{i}", data=[f"/e{i}", i, f"e{i}"]) for i in range(5)], 0)
    s.fill = fill
    s.selection_changed = lambda: None
    top = subdir("/a", 3, None)
    setattr(proc, attr, subdir("/a/b", 2, top))
    return s, proc, top


@pytest.mark.parametrize("cls,attr", [(Preset, "preset_subdir_info"), (Bank, "bank_subdir_info")])
def test_up_level_goes_up_one_folder(app, cls, attr):
    s, proc, top = screen(cls, attr)
    assert s.up_level()
    assert getattr(proc, attr) is top and s.index == 2
    assert s.up_level()
    assert getattr(proc, attr) is None and s.index == 3
    assert not s.up_level()
    assert s.fills == [top, None]


def test_bank_up_level_leaves_the_preset_folder(app):
    s, proc, _ = screen(Bank, "bank_subdir_info")
    proc.preset_subdir_info = subdir("/p", 1, None)
    s.up_level()
    assert proc.preset_subdir_info is None


def in_folder(ui, screen, attr):
    """ui shows screen (chain control -> screen) inside a sub-folder of a sub-folder"""
    proc = ui.current_processor
    top = subdir("/a", 3, None)
    setattr(proc, attr, subdir("/a/b", 2, top))
    ui.show_screen("chain_control")
    ui.show_screen(screen)
    return proc, top


@pytest.mark.parametrize("screen,attr", [("preset", "preset_subdir_info"), ("bank", "bank_subdir_info")])
def test_back_leaves_the_list_as_tk(app, screen, attr):
    ui = nav_ui(banks=3)
    in_folder(ui, screen, attr)
    ui.back()
    assert ui.current_screen == "chain_control"


def test_switch_1_in_a_preset_folder_shows_the_banks_as_tk(app):
    ui = nav_ui(banks=3)
    in_folder(ui, "preset", "preset_subdir_info")
    ui.zynswitch(1, "S")
    assert ui.current_screen == "bank"


def test_switch_1_in_a_bank_folder_goes_back_as_tk(app):
    ui = nav_ui(banks=3)
    proc, top = in_folder(ui, "bank", "bank_subdir_info")
    ui.zynswitch(1, "S")
    assert ui.current_screen == "chain_control"


@pytest.mark.parametrize("screen,attr,then", [("preset", "preset_subdir_info", "bank"),
                                              ("bank", "bank_subdir_info", "chain_control")])
def test_left_goes_up_one_folder_then_as_switch_1(app, screen, attr, then):
    ui = nav_ui(banks=3)
    proc, top = in_folder(ui, screen, attr)
    ui._navigate("left")
    assert getattr(proc, attr) is top and ui.current_screen == screen
    ui._navigate("left")
    assert getattr(proc, attr) is None and ui.current_screen == screen
    ui._navigate("left")
    assert ui.current_screen == then


def test_bank_preset_in_a_bank_folder_goes_up_one_folder(app, monkeypatch):
    ui = switch_ui(monkeypatch, "bank")
    proc = ui.current_processor
    top = subdir("/a", 3, None)
    proc.bank_subdir_info = subdir("/a/b", 2, top)
    ui.cuia__zynswitch([CTRL, "S"])   # BANK_PRESET by the custom switch rule
    assert proc.bank_subdir_info is top and ui.current_screen == "bank"
    proc.bank_subdir_info = None
    ui.cuia__zynswitch([CTRL, "S"])
    assert ui.current_screen == "chain_control"


def test_bank_preset_keeps_the_audio_player_in_its_file_lists(app, monkeypatch):
    """Tk's is_shown_audio_player: the current processor is the audio player; Qt reset it to the
    active chain's outside the audio player's own screen, so BANK_PRESET in its file list showed
    the chain's banks"""
    ui = switch_ui(monkeypatch, "preset")
    player = ui.current_processor
    ui.state_manager.audio_player = player
    ui.chain_manager.get_active_chain().current_processor = SimpleNamespace(eng_code="SY")
    top = subdir("/a", 3, None)
    player.preset_subdir_info = subdir("/a/b", 2, top)
    ui.cuia_bank_preset()
    assert ui.current_processor is player and player.preset_subdir_info is top
