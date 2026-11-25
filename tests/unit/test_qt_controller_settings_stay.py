"""A controller setting changed in Admin > Controller Settings stays there (the user's report: after
the pattern editor, choosing an option led back to the pattern editor): the options list is no
screen of the history. MENU on the pattern editor shows its options, MENU again the main menu;
kept in the history, that options list ended the history at itself when the setting's options
list was shown (show_screen's pruning), and closing it returned to the pattern editor."""

from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6.QtCore")
ui_mod = pytest.importorskip("zynqt.ui")

from tests.fakes.ctrldev_settings import JAM, FakeCtrldevManager, FakeSettingsDriver  # noqa: E402
from tests.unit.test_qt_gui_thread import app  # noqa: E402,F401
from tests.unit.test_qt_screen_signals import screen_ui  # noqa: E402
from zynqt.screens.controller_settings import ControllerSettings  # noqa: E402
from zynqt.screens.snapshots import Options  # noqa: E402

ZynUI = ui_mod.ZynUI


def stub(**kwargs):
    return SimpleNamespace(build=lambda: None, hide=lambda: None, back=lambda: False, **kwargs)


def settings_ui():
    ui = screen_ui()
    ui.chain_manager = None
    ui._help_html = ui._value_editor = ui._keyboard_action = ui._confirm_action = None
    ui._moving_chain, ui._moving_processor = False, None
    for name in ("back", "close_screen", "show_options", "cuia_menu", "showScreen", "_screen_obj",
                 "_overlay_shown"):
        setattr(ui, name, getattr(ZynUI, name).__get__(ui))
    ui.jam = FakeSettingsDriver("DrivenByMoss JAM", JAM)
    ui.state_manager.ctrldev_manager = FakeCtrldevManager([], [ui.jam])
    ui.list_screens["controller_settings"] = ControllerSettings(ui)
    ui.list_screens["option"] = Options(ui)
    ui.list_screens["main_menu"] = stub()
    ui.list_screens["launcher"] = stub()
    # The pattern editor's menu: its options (Pattern options)
    ui.qml_screen_objects["pattern_editor"] = stub(
        show_menu=lambda: ui.show_options("Pattern options", [("Clear", lambda: None, None, None)]))
    return ui


def choose(screen, text):
    screen.activate(next(i for i, e in enumerate(screen.entries) if text in e["title"]), "S")


@pytest.mark.parametrize("before, menus", [("pattern_editor", 2), ("pattern_editor", 0), ("mixer", 1),
                                           ("launcher", 1)])
def test_a_setting_chosen_stays_in_controller_settings(app, before, menus):
    ui = settings_ui()
    ui.show_screen(before)
    for _ in range(menus):
        ui.cuia_menu()     # the pattern editor: its options, then the main menu
    if menus:
        assert ui.current_screen == "main_menu"
    ui.show_screen("admin")
    ui.show_screen("controller_settings")
    cs = ui.list_screens["controller_settings"]
    try:
        choose(cs, "DrivenByMoss JAM")
        choose(cs, "Hardware Setup")
        choose(cs, "LED Brightness")
        assert ui.current_screen == "option"
        choose(ui.list_screens["option"], "Dim")
        assert ui.jam.calls == [(1, "Dim")]
        assert ui.current_screen == "controller_settings"
        assert cs.title == "Hardware Setup"
        # BACK goes up the levels, then to Admin
        for _ in range(2):
            ui.back()
            assert ui.current_screen == "controller_settings"
        ui.back()
        assert ui.current_screen == "admin"
    finally:
        cs.hide()


def test_back_from_a_screen_shown_over_the_options_list(app):
    """MENU on the pattern editor's options: BACK from the main menu goes to the pattern editor"""
    ui = settings_ui()
    ui.show_screen("pattern_editor")
    ui.cuia_menu()
    ui.cuia_menu()
    assert "option" not in ui.screen_history
    ui.back()
    assert ui.current_screen == "pattern_editor"
