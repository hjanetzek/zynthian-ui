"""Tk's custom switch rule (zynthian_gui.custom_switch_ui_action / check_current_screen_switch, the
"BIG ÑAPA"): a short press on a custom switch runs its bold action when the switch belongs to the
screen shown: its bold action is BANK_PRESET in the bank / preset list or the audio player, its
short action ends with the screen's name, or it is MENU in the main menu or the chain manager. It
comes before ALT's actions. The V5's CTRL key (CUSTOM_SWITCH_03: S CHAIN_CONTROL, B BANK_PRESET;
the Duet's keypad too): chain control -> the presets -> the banks -> back ("Short press CTRL
button to access the bank list. Short press CTRL again to exit bank/preset selection", the V5
manual). The Qt UI lacked the BANK_PRESET clause, so short CTRL in the preset list reopened
chain control and the banks were out of reach on the Duet."""

from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6.QtCore")
ui_mod = pytest.importorskip("zynqt.ui")

from tests.unit.test_qt_gui_thread import app  # noqa: E402,F401
from tests.unit.test_qt_preset_back_to_banks import preset_ui  # noqa: E402
from zyngui import zynthian_gui_config  # noqa: E402
from zynqt.keypad_leds import current_screen_switch  # noqa: E402
from zynqt.screens.chain_screens import Bank  # noqa: E402

ZynUI = ui_mod.ZynUI


def nav_ui(banks=3):
    ui = preset_ui(banks)
    bank = ui.list_screens["bank"] = Bank(ui)
    bank.fill = lambda: None
    return ui

# The V5 wiring profile's custom switches (zynthian-sys config/wiring-profiles/v5_zynface), from
# CUSTOM_SWITCH_01 (switch 4)
V5 = [
    {"S": "MENU", "B": "SCREEN_ADMIN"},
    {"S": "SCREEN_AUDIO_MIXER", "B": "SCREEN_ALSA_MIXER"},
    {"S": "CHAIN_CONTROL", "B": "BANK_PRESET"},
    {"S": "SCREEN_ZS3", "B": "SCREEN_SNAPSHOT"},
    {"S": "TOGGLE_ALT_MODE", "B": "HELP"},
    {"S": "", "B": ""},
    {"S": "SCREEN_LAUNCHER", "B": "SCREEN_PATTERN_EDITOR", "AS": "TEMPO"},
]
CTRL = 6   # CUSTOM_SWITCH_03


@pytest.mark.parametrize("screen,i,expected", [
    ("chain_control", 2, True),    # CHAIN_CONTROL
    ("preset", 2, True),           # BANK_PRESET's screens
    ("bank", 2, True),
    ("audio_player", 2, True),
    ("zs3", 3, True),              # SCREEN_ZS3
    ("mixer", 1, True),            # SCREEN_AUDIO_MIXER
    ("launcher", 6, True),         # SCREEN_LAUNCHER
    ("main_menu", 0, True),        # MENU
    ("chain_manager", 0, True),
    ("mixer", 2, False),
    ("admin", 0, False),
    ("snapshot", 3, False),
    ("preset", 1, False),
    ("mixer", 5, False),           # no actions
    ("", 2, False),
])
def test_the_rule(screen, i, expected):
    assert current_screen_switch(V5[i], screen) is expected


def switch_ui(monkeypatch, screen):
    monkeypatch.setattr(zynthian_gui_config, "custom_switch_ui_actions", V5, raising=False)
    ui = nav_ui(banks=3)
    ui.alt_mode = False
    ran = []

    def run(cuia, params):
        ran.append(cuia)
        func = {"bank_preset": ui.cuia_bank_preset}.get(cuia.lower())
        if func:
            func(params)
    ui._run_cuia = run
    ui.ran = ran
    for name in ("cuia__zynswitch", "_push_action", "_is_current_screen_switch", "cuia_bank_preset",
                 "replace_screen"):
        setattr(ui, name, getattr(ZynUI, name).__get__(ui))
    ui.state_manager.audio_player = None
    chain = SimpleNamespace(current_processor=ui.current_processor)
    ui.chain_manager = SimpleNamespace(get_active_chain=lambda: chain)
    ui.list_screens["preset"].is_flat = lambda proc: False
    ui.show_screen("chain_control")
    if screen != "chain_control":
        ui.show_screen(screen)
    return ui


def test_ctrl_short_in_chain_control_shows_the_presets(app, monkeypatch):
    ui = switch_ui(monkeypatch, "chain_control")
    ui.list_screens["chain_control"].switch = lambda i, t: False
    ui.current_processor.preset_list = [["p0", 0, "Preset 0"]]
    ui.cuia__zynswitch([CTRL, "S"])
    assert ui.ran == ["BANK_PRESET"]
    assert ui.current_screen == "preset"


@pytest.mark.parametrize("flat", [False, True])
def test_ctrl_short_in_the_presets_shows_the_banks_then_leaves(app, monkeypatch, flat):
    ui = switch_ui(monkeypatch, "preset")
    ui.list_screens["preset"].flat = flat
    ui.cuia__zynswitch([CTRL, "S"])
    assert ui.ran == ["BANK_PRESET"]
    assert ui.current_screen == "bank"
    assert ui.screen_history == ["mixer", "chain_control"]
    ui.cuia__zynswitch([CTRL, "S"])
    assert ui.current_screen == "chain_control"


def test_ctrl_short_in_a_preset_sub_folder_goes_up_first(app, monkeypatch):
    ui = switch_ui(monkeypatch, "preset")
    proc = ui.current_processor
    proc.preset_subdir_info = ["/sub", 0, "Sub", None]
    ui.cuia__zynswitch([CTRL, "S"])
    assert proc.preset_subdir_info is None and ui.current_screen == "preset"


def test_a_screen_name_match_runs_the_bold_action(app, monkeypatch):
    ui = switch_ui(monkeypatch, "zs3")
    ui.list_screens["zs3"].switch = lambda i, t: False
    ui.cuia__zynswitch([7, "S"])   # SCREEN_ZS3 in the ZS3 list
    assert ui.ran == ["SCREEN_SNAPSHOT"]


def test_menu_in_the_main_menu_runs_the_bold_action(app, monkeypatch):
    ui = switch_ui(monkeypatch, "chain_control")
    ui.list_screens["main_menu"] = SimpleNamespace(build=lambda: None, hide=lambda: None)
    ui.show_screen("main_menu")
    ui.cuia__zynswitch([4, "S"])
    assert ui.ran == ["SCREEN_ADMIN"]


def test_other_keys_and_screens_keep_the_short_action(app, monkeypatch):
    ui = switch_ui(monkeypatch, "zs3")
    ui.list_screens["zs3"].switch = lambda i, t: False
    ui.cuia__zynswitch([CTRL, "S"])   # CHAIN_CONTROL in the ZS3 list
    ui.cuia__zynswitch([4, "S"])      # MENU
    ui.cuia__zynswitch([7, "B"])      # bold: unchanged
    assert ui.ran == ["CHAIN_CONTROL", "MENU", "SCREEN_SNAPSHOT"]


def test_the_rule_comes_before_alt(app, monkeypatch):
    ui = switch_ui(monkeypatch, "chain_control")
    ui.list_screens["launcher"] = SimpleNamespace(build=lambda: None, hide=lambda: None)
    ui.show_screen("launcher")
    ui.alt_mode = True
    ui.cuia__zynswitch([10, "S"])   # SCREEN_LAUNCHER (ALT: TEMPO) in the launcher
    assert ui.ran == ["SCREEN_PATTERN_EDITOR"]
    ui.show_screen("chain_control")
    ui.list_screens["chain_control"].switch = lambda i, t: False
    ui.cuia__zynswitch([10, "S"])
    assert ui.ran[-1] == "TEMPO"
