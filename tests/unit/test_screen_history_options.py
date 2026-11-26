"""The screen history with the options list ("option"), a screen every caller configures anew.

Showing a screen again ends the history where it was (prune_screen_history): BACK from it doesn't
return to itself. For the options list that cut the history at an older, unrelated list: the
pattern editor's MENU (its options), MENU again (the main menu), Admin, an options list of Admin
(Touch Navigation): BACK, or choosing the current value, returned to the pattern editor instead
of Admin. Reproduced in upstream's Tk UI (QEMU, 2026-11-26).

zynthian_gui can't be built in tests (its __init__ starts the whole UI): show_screen and
close_screen run on a bare instance (``__new__``) with stub screens.
"""

import threading
from types import SimpleNamespace

from zyngui.zynthian_gui import zynthian_gui


def screen():
    return SimpleNamespace(build_view=lambda: True, show=lambda: None, hide=lambda: None,
                           back_action=lambda: False, launcher_mode=False,
                           set_launcher_mode=lambda mode: None)


def make_gui():
    gui = zynthian_gui.__new__(zynthian_gui)
    gui.screen_lock = threading.Lock()
    gui.screen_timer_id = None
    gui.current_screen = None
    gui.screen_history = []
    gui.wsleds = gui.wsleds_v5touch = None
    gui.chain_manager = SimpleNamespace(restore_presets=lambda: None,
                                        active_chain=SimpleNamespace(current_processor=None))
    gui.screens = {name: screen() for name in ("mixer", "launcher", "pattern_editor", "main_menu", "admin",
                                               "option", "chain_control", "bank", "preset")}
    gui.show_screen_reset("mixer")
    return gui


def test_back_from_an_admin_options_list_after_the_pattern_editors_menu():
    gui = make_gui()
    gui.show_screen("pattern_editor")
    gui.show_screen("option")        # MENU: the pattern options
    gui.show_screen("main_menu")     # MENU again
    gui.show_screen("admin")
    gui.show_screen("option")        # an admin setting's options
    assert gui.screen_history == ["mixer", "pattern_editor", "main_menu", "admin", "option"]
    gui.back_screen()
    assert gui.current_screen == "admin"
    gui.back_screen()
    assert gui.current_screen == "main_menu"
    gui.back_screen()
    assert gui.current_screen == "pattern_editor"


def test_an_option_chosen_returns_to_the_screen_that_opened_the_list():
    """zynthian_gui_option.select_action closes the list (close_on_select) before the callback"""
    gui = make_gui()
    for name in ("pattern_editor", "option", "main_menu", "admin", "option"):
        gui.show_screen(name)
    gui.close_screen()
    assert gui.current_screen == "admin"


def test_other_screens_shown_again_still_end_the_history_there():
    gui = make_gui()
    for name in ("chain_control", "bank", "preset", "chain_control"):
        gui.show_screen(name)
    assert gui.screen_history == ["mixer", "chain_control"]
    gui.back_screen()
    assert gui.current_screen == "mixer"
