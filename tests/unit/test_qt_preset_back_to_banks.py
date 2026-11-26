"""BACK on the kits (switch 1 short, the keyboard's Escape) in the preset list goes to the bank list
when the processor has more than one bank, as zynthian_gui_preset.switch, also from the flat list
(all banks under section titles: LV2 plugins, sfizz). The user's report: once in the presets,
there was no way back to the banks; the flat list left on BACK, and chain control and
BANK_PRESET open the flat list directly. Checked in upstream's Tk UI (QEMU, Dexed,
2026-11-26): ZYNSWITCH 1 S in the presets shows the banks, BACK from there chain control; the BACK
CUIA (the V5's BACK key) goes back to chain control."""

from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6.QtCore")
ui_mod = pytest.importorskip("zynqt.ui")

from tests.unit.test_qt_gui_thread import app  # noqa: E402,F401
from tests.unit.test_qt_screen_signals import screen_ui  # noqa: E402
from zynqt.screens.chain_screens import Preset  # noqa: E402

ZynUI = ui_mod.ZynUI


def proc(banks):
    p = SimpleNamespace(eng_code="SY", show_fav_presets=False, preset_subdir_info=None, bank_subdir_info=None,
                        get_bank_list=lambda: [[f"b{i}", i, f"Bank {i}"] for i in range(banks)])

    def toggle():
        p.show_fav_presets = not p.show_fav_presets
    p.toggle_show_fav_presets = toggle
    return p


def preset_ui(banks, flat=False):
    ui = screen_ui()
    ui.chain_manager = None
    ui._help_html = ui._value_editor = ui._keyboard_action = ui._confirm_action = None
    ui._moving_chain, ui._moving_processor = False, None
    for name in ("back", "close_screen", "zynswitch", "_screen_obj", "_overlay_shown", "purge_history"):
        setattr(ui, name, getattr(ZynUI, name).__get__(ui))
    ui.current_processor = proc(banks)
    ui.list_screens["chain_control"] = SimpleNamespace(build=lambda: None, hide=lambda: None, back=lambda: False)
    ui.list_screens["bank"].back = lambda: False
    preset = ui.list_screens["preset"] = Preset(ui)
    preset.fill = lambda keep=False: preset.fills.append(ui.current_processor.show_fav_presets)
    preset.fills = []
    preset.flat = flat
    return ui


@pytest.mark.parametrize("via_bank", [False, True])
@pytest.mark.parametrize("flat", [False, True])
def test_switch_1_in_the_presets_shows_the_banks(app, via_bank, flat):
    ui = preset_ui(banks=3, flat=flat)
    ui.show_screen("chain_control")
    if via_bank:
        ui.show_screen("bank")
    ui.show_screen("preset")
    ui.zynswitch(1, "S")
    assert ui.current_screen == "bank"
    assert ui.screen_history == ["mixer", "chain_control"]
    ui.zynswitch(1, "S")
    assert ui.current_screen == "chain_control"


def test_switch_1_with_one_bank_goes_back(app):
    ui = preset_ui(banks=1)
    ui.show_screen("chain_control")
    ui.show_screen("preset")
    ui.zynswitch(1, "S")
    assert ui.current_screen == "chain_control"


def test_the_back_cuia_goes_back_as_in_tk(app):
    ui = preset_ui(banks=3)
    ui.show_screen("chain_control")
    ui.show_screen("preset")
    ui.back()
    assert ui.current_screen == "chain_control"


def test_switch_2_toggles_the_favourites(app):
    ui = preset_ui(banks=3)
    ui.show_screen("chain_control")
    ui.show_screen("preset")
    fills = ui.list_screens["preset"].fills
    del fills[:]
    ui.zynswitch(2, "S")
    ui.zynswitch(2, "S")
    assert fills == [True, False]
    assert ui.current_screen == "preset"
