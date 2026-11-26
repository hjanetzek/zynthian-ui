"""BACK in the bank and preset lists' sub-folders (the audio player's folders, FluidSynth's bank
directories) goes up one folder, as zynthian_gui_bank / zynthian_gui_preset.browse_back: the
parent's info ([3]) and the folder left selected ([1]); the Qt lists left all sub-folders at
once."""

from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6.QtCore")

from tests.unit.test_qt_gui_thread import app  # noqa: E402,F401
from zynqt.screens.base import entry  # noqa: E402
from zynqt.screens.chain_screens import Bank, Preset  # noqa: E402


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
def test_back_goes_up_one_folder(app, cls, attr):
    s, proc, top = screen(cls, attr)
    assert s.back()
    assert getattr(proc, attr) is top and s.index == 2
    assert s.back()
    assert getattr(proc, attr) is None and s.index == 3
    assert not s.back()
    assert s.fills == [top, None]


def test_bank_back_leaves_the_preset_folder(app):
    s, proc, _ = screen(Bank, "bank_subdir_info")
    proc.preset_subdir_info = subdir("/p", 1, None)
    s.back()
    assert proc.preset_subdir_info is None
