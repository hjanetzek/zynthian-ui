"""The Qt UI's screen names for drivers (zynqt.screen_names, ZynUI.notify_screen /
qt_screen_name):

- every screen change sends SS_GUI_SHOW_SCREEN with the Tk name, once the screen is current, from
  the GUI thread also when the change was asked for in another thread;
- Tk names (control, root, zynpad, pated, ...) open the Qt screens;
- zyngui.screens for drivers: stand-ins of the Tk screens they use (zynqt.tk_screens)."""

import threading
from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6.QtCore")
ui_mod = pytest.importorskip("zynqt.ui")

from tests.unit.test_qt_gui_thread import app, in_thread, wait_for  # noqa: E402,F401
from zyngine.zynthian_signal_manager import zynsigman  # noqa: E402
from zynqt.gui_thread import GuiCaller  # noqa: E402
from zynqt import screen_names  # noqa: E402

ZynUI = ui_mod.ZynUI


# Screens: a ZynUI stand-in with what show_screen / _set_current_screen use

PLAYER = object()


def screen_ui(gui=None):
    ui = SimpleNamespace(current_screen="mixer", screen_history=[], _last_root="mixer", _sent_screen=None,
                         current_processor=None, qml_screen_objects={}, infos=[],
                         list_screens={n: SimpleNamespace(build=lambda: None, hide=lambda: None)
                                       for n in ("bank", "preset", "zs3", "admin", "midi_in", "midi_out")},
                         state_manager=SimpleNamespace(audio_player=PLAYER),
                         pattern_editor=SimpleNamespace(cc_mode=False),
                         chain_control_screen=SimpleNamespace(special_processor=None),
                         currentScreenChanged=SimpleNamespace(emit=lambda: None))
    ui._gui = gui or SimpleNamespace(in_gui_thread=lambda: True)
    for name in ("helpClose", "endMoveChain", "endMoveProcessor", "setup_zynpots"):
        setattr(ui, name, lambda: None)
    ui.show_info = lambda text, ms=2500: ui.infos.append(text)
    for name in ("show_screen", "replace_screen", "show_screen_reset", "_set_current_screen", "notify_screen",
                 "qt_screen_name", "get_current_screen"):
        setattr(ui, name, getattr(ZynUI, name).__get__(ui))
    ui.state_manager.tempo_processor = SimpleNamespace(refresh_controllers=lambda params: None)
    ui.state_manager.alsa_mixer_processor = SimpleNamespace(refresh_controllers=lambda params: None)
    return ui


@pytest.fixture
def driver():
    """A controller driver's view: the screens it is told, and what the UI shows then"""
    seen = []
    ui_ref = {}

    def on_screen(screen, **kwargs):
        seen.append((screen, ui_ref["ui"].current_screen, kwargs))

    zynsigman.register(zynsigman.S_GUI, zynsigman.SS_GUI_SHOW_SCREEN, on_screen)
    yield seen, ui_ref
    zynsigman.unregister(zynsigman.S_GUI, zynsigman.SS_GUI_SHOW_SCREEN, on_screen)


def test_screen_changes_send_the_tk_names(driver):
    seen, ui_ref = driver
    ui = ui_ref["ui"] = screen_ui()
    for name in ("chain_control", "chain_control", "mixer", "launcher", "midi_in", "midi_out", "pattern_editor",
                 "tempo", "bank", "preset", "zs3", "admin"):
        ui.show_screen(name)
    ui.pattern_editor.cc_mode = True
    ui.show_screen("pattern_editor")
    ui.pattern_editor.cc_mode = False
    ui.notify_screen()   # PatternEditor.toggleCcMode
    assert [s for s, _, _ in seen] == ["chain_control", "mixer", "launcher", "midi_config", "pattern_editor",
                                       "tempo", "bank", "preset", "zs3", "admin", "pated_cc", "pattern_editor"]
    # Sent once the screen is current, with nothing but the name (as Tk)
    assert all(kw == {} for _, _, kw in seen)
    assert [cur for _, cur, _ in seen][:4] == ["chain_control", "mixer", "launcher", "midi_in"]
    assert ui.get_current_screen() == "pattern_editor"


def test_back_sends_too(driver):
    seen, ui_ref = driver
    ui = ui_ref["ui"] = screen_ui()
    ui.show_screen("bank")
    ui._set_current_screen("mixer")   # ZynUI.back()
    assert [s for s, _, _ in seen] == ["bank", "mixer"]


def test_screen_from_a_worker_thread(app, driver):
    seen, ui_ref = driver
    ui = ui_ref["ui"] = screen_ui(GuiCaller())
    threads = []
    ui.setup_zynpots = lambda: threads.append(threading.get_ident())
    in_thread(lambda: ui.show_screen_reset("control"))
    assert ui.current_screen == "mixer"   # not yet: posted
    assert wait_for(app, lambda: ui.current_screen == "chain_control")
    assert threads == [threading.get_ident()]
    assert [s for s, _, _ in seen] == ["chain_control"]


def test_tk_names_open_the_qt_screens():
    ui = screen_ui()
    q = ui.qt_screen_name
    assert q("control") == "chain_control"
    assert q("zynpad") == q("arranger") == "launcher"
    assert q("pated") == q("pated_cc") == "pattern_editor"
    assert q("midi_config") == "midi_in"
    assert q("root") == "mixer"
    assert q("bank") == "bank" and q("chain_control") == "chain_control"
    assert q(None) == "mixer"
    ui.current_processor = PLAYER
    assert q("control") == "audio_player"
    ui.show_screen("launcher")
    ui.show_screen("bank")
    assert q("root") == "launcher"


def test_show_screen_reset_control_has_no_message():
    """The Duet case: show_screen_reset("control") showed "'control' is not in the Qt UI yet." """
    ui = screen_ui()
    ui.show_screen_reset("control")
    assert ui.current_screen == "chain_control"
    assert ui.infos == []
    ui.show_screen("wifi")   # a Tk screen the Qt UI doesn't have
    assert ui.infos == ["'wifi' is not in the Qt UI yet."]


def test_name_map_covers_both_uis():
    qt_screens = set(ui_mod.QML_SCREENS) | {"main_menu", "add_chain", "engine", "midi_chan", "bank", "preset",
                                            "option", "snapshot", "chain_options", "audio_in", "audio_out",
                                            "midi_in", "midi_out", "processor_options", "midi_devices_in",
                                            "midi_devices_out", "zs3", "admin", "midi_recorder", "midi_cc"}
    # Every Tk name of a Qt screen opens a Qt screen again
    for screen in qt_screens:
        assert screen_names.qt_name(screen_names.tk_name(screen)) in qt_screens
    # Tk aliases point at Qt screens; Tk-only names aren't Qt screens
    assert set(screen_names.TK_TO_QT.values()) <= qt_screens
    assert not set(screen_names.TK_ONLY) & qt_screens


# zyngui.screens for drivers (zynqt.tk_screens)

def shim_ui(gui=None):
    calls = []
    rec = lambda name: (lambda *a: calls.append((name, threading.get_ident())))   # noqa: E731
    ui = SimpleNamespace(current_screen="mixer", calls=calls, _gui=gui or GuiCaller(),
                         launcher=SimpleNamespace(edit_pad=rec("edit_pad"),
                                                  padsChanged=SimpleNamespace(emit=rec("padsChanged"))),
                         pattern_editor=SimpleNamespace(undo=rec("undo"), redo=rec("redo"), cursor=[3, 60],
                                                        pattern=7, _shown=False))
    ui.show_screen = lambda name: calls.append((f"show {name}", threading.get_ident()))
    return ui


def test_tk_screens_shims(app):
    from zynqt.tk_screens import TkScreens
    ui = shim_ui()
    screens = TkScreens(ui)
    assert screens["mixer"].launcher_mode is False
    ui.current_screen = "launcher"
    assert screens["launcher"].launcher_mode is True
    assert screens["pattern_editor"].selected_cell == [3, 60]
    assert screens["pattern_editor"].pattern == 7
    screens["arranger"].select_cell(1, 2)   # ignored (disabled in base_ui)
    with pytest.raises(KeyError):
        screens["zynpad"]
    # Actions from a driver's MIDI thread run in the GUI thread
    in_thread(lambda: (screens["mixer"].edit_pad(), screens["pattern_editor"].undo_pattern(),
                       screens["pattern_editor"].redo_pattern(), screens["launcher"].refresh_launchers()))
    assert wait_for(app, lambda: len(ui.calls) == 4)
    main = threading.get_ident()
    posted = [(c, t) for c, t in ui.calls if c != "padsChanged"]   # a signal: emitted from any thread
    assert [c for c, _ in posted] == ["edit_pad", "undo", "redo"]
    assert all(t == main for _, t in posted)
    screens["launcher"].set_launcher_mode(False)
    assert ui.calls[-1][0] == "show mixer"
