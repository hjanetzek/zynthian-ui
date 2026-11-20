"""ZYNPOT (turn an encoder by a relative amount) in the Qt UI, as zynthian_gui.cuia_zynpot:

- from cuia_queue (OSC, MIDI, key bindings, controller drivers) and run directly (custom switch
  actions, QML, callable_ui_action), with numbers or strings (CUIA strings, untyped OSC);
- bad parameters are logged and must not end the CUIA thread;
- the current screen's zynpot(i, d) gets it; elsewhere the select knob moves the list selection;
  a dialog shown takes the encoders (value editor, help, moving a chain);
- the screens: mixer (levels, balance, chain), chain control (controllers; select mode: pages,
  processors), launcher (phrase), pattern editor (zoom, row, step)."""

from queue import Queue
from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6.QtCore")
ui_mod = pytest.importorskip("zynqt.ui")

from zyngui import zynthian_gui_config  # noqa: E402

ZynUI = ui_mod.ZynUI
SELECT = 3


@pytest.fixture(autouse=True)
def layout(monkeypatch):
    monkeypatch.setattr(zynthian_gui_config, "select_ctrl", SELECT, raising=False)
    monkeypatch.setattr(zynthian_gui_config, "layout", {"ctrl_order": (0, 1, 2, 3)}, raising=False)


def bind(obj, cls, *names):
    for name in names:
        setattr(obj, name, getattr(cls, name).__get__(obj))
    return obj


# Dispatch: a ZynUI stand-in with what the CUIA thread and the zynpot dispatch use

class FakeScreen:
    def __init__(self, takes=True):
        self.turns = []
        self.takes = takes

    def zynpot(self, i, d):
        self.turns.append((i, d))
        return self.takes


def fake_ui(screen=None, current="mixer", list_screens=None):
    ui = SimpleNamespace(current_screen=current, list_screens=list_screens or {}, qml_screen_objects={},
                         infos=[], navigated=[], emitted=[], steps=[], scrolled=[],
                         _help_html="", _value_editor=None, _keyboard_action=None, _confirm_action=None,
                         _moving_chain=False, _moving_processor=None, exit_flag=False,
                         zynswitch_autolong_disabled=False, zynpot_pr_state=[0, 0, 0, 0],
                         cuia_queue=Queue(), state_manager=SimpleNamespace(set_event_flag=lambda: None))
    ui._screen_obj = lambda: screen
    ui.show_info = lambda text, ms=2500: ui.infos.append(text)
    ui._navigate = ui.navigated.append
    ui.valueEditorStep = ui.steps.append
    ui.helpScroll = SimpleNamespace(emit=ui.scrolled.append)
    ui._switch_zynpot = lambda i: None
    ui._cuiaRequested = SimpleNamespace(emit=lambda name, params: ui.emitted.append((name, list(params))))
    return bind(ui, ZynUI, "_run_cuia", "cuia_zynpot", "cuia__zynpot", "_overlay_zynpot", "_overlay_shown",
                "_cuia_task")


def run_queue(ui, *events):
    """The CUIA thread over these events (it ends at __EXIT__); the CUIAs it hands to the GUI"""
    for e in events:
        ui.cuia_queue.put_nowait(e)
    ui.cuia_queue.put_nowait("__EXIT__")
    ui._cuia_task()
    return ui.emitted


@pytest.mark.parametrize("event", [
    ("ZYNPOT", (3, 1), "osc"),            # typed OSC
    ("ZYNPOT", ("3", "1"), "osc"),        # untyped OSC (strings)
    ("ZYNPOT", ("3", "1.0"), "osc"),
    ("ZYNPOT", (3.0, 1.0), "osc"),        # OSC floats
    ("zynpot", ["3", "1"]),               # MIDI CUIA, drivers (state_manager.send_cuia)
    "zynpot 3,1",                         # CUIA string
])
def test_queue_zynpot_numbers_or_strings(event):
    ui = fake_ui()
    assert run_queue(ui, event) == [("_zynpot", [3, 1])]


def test_queue_zynpot_negative_delta():
    assert run_queue(fake_ui(), ("ZYNPOT", ("0", "-5"), "osc")) == [("_zynpot", [0, -5])]


@pytest.mark.parametrize("params", [(), ("3",), ("x", "1"), ("3", "fast"), (None, 1)])
def test_queue_zynpot_bad_parameters_skipped_thread_goes_on(params):
    ui = fake_ui()
    emitted = run_queue(ui, ("ZYNPOT", params, "osc"), ("ZYNPOT_ABS", ("0", "0.5"), "osc"))
    assert emitted == [("ZYNPOT_ABS", ["0", "0.5"])]


def test_queue_zynpot_held_key_repeats_until_release():
    ui = fake_ui()
    emitted = run_queue(ui, "zynpot 3,1,P", "zynpot 3,1,R")
    assert emitted == [("_zynpot", [3, 1])]


@pytest.mark.parametrize("params", [[0, 5], ["0", "5"], ["0", "5.0"]])
def test_direct_zynpot_reaches_the_screen(params):
    # Custom switch actions / QML / callable_ui_action run ZYNPOT through _run_cuia: before, the
    # Qt UI had no cuia_zynpot ("ZYNPOT: not in the Qt UI yet", nothing turned)
    screen = FakeScreen()
    ui = fake_ui(screen)
    ui._run_cuia("ZYNPOT", params)
    assert screen.turns == [(0, 5)]
    assert ui.infos == []


@pytest.mark.parametrize("params", [[], ["0"], ["a", "b"]])
def test_direct_zynpot_bad_parameters_do_nothing(params):
    screen = FakeScreen()
    ui = fake_ui(screen)
    ui._run_cuia("ZYNPOT", params)
    assert screen.turns == []
    assert ui.infos == []


def test_queue_path_reaches_the_screen():
    screen = FakeScreen()
    ui = fake_ui(screen)
    for name, params in run_queue(ui, ("ZYNPOT", ("1", "-2"), "osc")):
        ui._run_cuia(name, params)
    assert screen.turns == [(1, -2)]


def test_list_screen_select_knob_moves_the_selection():
    moves = []
    lst = SimpleNamespace(move=moves.append)
    ui = fake_ui(lst, current="admin", list_screens={"admin": lst})
    ui._run_cuia("ZYNPOT", ["3", "2"])
    ui._run_cuia("ZYNPOT", [0, 2])      # not the select knob: nothing (zynthian_gui_selector)
    assert moves == [2]


def test_screen_not_taking_the_knob_select_navigates():
    screen = FakeScreen(takes=False)
    ui = fake_ui(screen, current="main_menu")
    ui._run_cuia("ZYNPOT", [3, -1])
    ui._run_cuia("ZYNPOT", [3, 1])
    assert ui.navigated == ["up", "down"]


# Dialogs over the screens take the encoders

def test_value_editor_takes_the_knobs():
    moves = []
    lst = SimpleNamespace(move=moves.append, zynpot=lambda i, d: moves.append((i, d)))
    ui = fake_ui(lst, current="admin", list_screens={"admin": lst})
    ui._value_editor = ["Tempo", 120, 10, 420, 1, 0, None]
    ui._run_cuia("ZYNPOT", [3, 2])      # ctrl_order[3]: steps
    ui._run_cuia("ZYNPOT", [2, -1])     # ctrl_order[2]: tens (zynthian_gui_base.zynpot_cb)
    ui._run_cuia("ZYNPOT", [0, 1])
    assert ui.steps == [2, -10]
    assert moves == []                  # not the list behind it


def test_value_editor_knobs_follow_the_layout(monkeypatch):
    monkeypatch.setattr(zynthian_gui_config, "layout", {"ctrl_order": (0, 2, 1, 3)})
    ui = fake_ui(FakeScreen())
    ui._value_editor = ["x", 0, 0, 100, 1, 0, None]
    ui._run_cuia("ZYNPOT", [1, 1])
    assert ui.steps == [10]


def test_help_scrolls_by_the_select_knob():
    ui = fake_ui(FakeScreen())
    ui._help_html = "<p>help</p>"
    ui._run_cuia("ZYNPOT", [3, -2])
    ui._run_cuia("ZYNPOT", [0, 1])
    assert ui.scrolled == [-1]


@pytest.mark.parametrize("dialog", ["_confirm_action", "_keyboard_action"])
def test_confirm_and_keyboard_take_no_knob(dialog):
    screen = FakeScreen()
    ui = fake_ui(screen)
    setattr(ui, dialog, lambda *a: None)
    ui._run_cuia("ZYNPOT", [3, 1])
    assert screen.turns == [] and ui.navigated == [] and ui.steps == []


def test_moving_chain_select_knob_moves_it():
    screen = FakeScreen()
    ui = fake_ui(screen)
    ui._moving_chain = True
    ui._run_cuia("ZYNPOT", [3, 1])
    assert ui.navigated == ["down"] and screen.turns == []


# The screens' zynpot(i, d) (unbound methods on stand-ins, as the other Qt screen tests)

class Zctrl:
    def __init__(self, value=0):
        self.value = value
        self.nudges = []

    def nudge(self, d, fine=False):
        self.nudges.append((d, fine))


def mixer_stand_in():
    from zynqt.screens.mixer_nav import MixerNav
    chains = {cid: SimpleNamespace(zynmixer_proc=SimpleNamespace(
        controllers_dict={"level": Zctrl(), "balance": Zctrl()})) for cid in (0, 2)}
    moved = []
    cm = SimpleNamespace(get_active_chain=lambda: chains[2], get_chain=chains.get, next_chain=moved.append)
    mixer = bind(SimpleNamespace(chain_manager=cm), MixerNav, "zynpot", "_mixer_ctrl")
    return mixer, chains, moved


def test_mixer_knobs():
    mixer, chains, moved = mixer_stand_in()
    for i, d in ((0, 5), (1, -2), (2, 3), (3, 1)):
        assert mixer.zynpot(i, d)
    assert chains[2].zynmixer_proc.controllers_dict["level"].nudges == [(5, False)]
    assert chains[2].zynmixer_proc.controllers_dict["balance"].nudges == [(-2, False)]
    assert chains[0].zynmixer_proc.controllers_dict["level"].nudges == [(3, False)]
    assert moved == [1]


def test_launcher_knobs(monkeypatch):
    from zynqt.models.launcher import Launcher
    mixer, chains, moved = mixer_stand_in()
    nav = []
    launcher = SimpleNamespace(moving_phrase=False, navigate=nav.append, _mixer=lambda: mixer)
    bind(launcher, Launcher, "zynpot")
    launcher.zynpot(2, 1)       # ctrl_order[2]: the phrase (Tk's mixer in launcher mode)
    launcher.zynpot(0, 4)
    assert nav == ["down"]
    assert chains[2].zynmixer_proc.controllers_dict["level"].nudges == [(4, False)]
    monkeypatch.setattr(zynthian_gui_config, "layout", {"ctrl_order": (0, 2, 1, 3)})
    launcher.zynpot(1, -1)      # V4: knob 1
    assert nav == ["down", "up"]


def chain_control_stand_in(mode="control"):
    from zynqt.screens.control import ChainControl
    nudged, pages, procs = [], [], []
    ctrls = [SimpleNamespace(index=n, zctrl=object(), nudge_fine=lambda d, fine, n=n: nudged.append((n, d, fine)))
             for n in range(4)]
    cc = SimpleNamespace(_widget_type="", _mode=mode, controllers=ctrls, isChain=True, midi_learning=0,
                         move_page=pages.append, _processor_step=procs.append,
                         ui=SimpleNamespace(zynpot_push_rotate=lambda i: False))
    bind(cc, ChainControl, "zynpot", "_knob_controller")
    return cc, nudged, pages, procs


def test_chain_control_knobs_turn_their_controllers():
    cc, nudged, pages, procs = chain_control_stand_in()
    for i in range(4):
        assert cc.zynpot(i, i + 1)
    assert nudged == [(0, 1, False), (1, 2, False), (2, 3, False), (3, 4, False)]


def test_chain_control_select_mode():
    cc, nudged, pages, procs = chain_control_stand_in("select")
    cc.zynpot(3, 2)
    cc.zynpot(2, -1)
    assert pages == [1] and procs == [-1] and nudged == []


def test_pattern_editor_knobs():
    from zynqt.screens import pattern_editor as pe_mod
    moved, zoom = [], []
    pe = SimpleNamespace(cc_mode=False, edit_mode=pe_mod.EDIT_MODE_NONE, zoom=4,
                         setZoom=zoom.append, move_cursor=lambda dx, dy: moved.append((dx, dy)))
    bind(pe, pe_mod.PatternEditor, "zynpot", "_ctrl")
    pe.zynpot(1, 1)     # zoom
    pe.zynpot(2, 1)     # row (up: the note above)
    pe.zynpot(3, -1)    # step
    assert zoom == [5]
    assert moved == [(0, -1), (-1, 0)]


# The kit's encoders (zyncore callback -> HwInput -> ZynUI._take_zynpots): the same dispatch

def test_hardware_encoder_deltas_reach_the_screen():
    from zynqt.hw_input import HwInput
    hw = HwInput(None, -1, 4, put_event=lambda e: None, has_ui_action=lambda i: False)
    screen = FakeScreen()
    ui = fake_ui(screen)
    ui.hw_input = hw
    bind(ui, ZynUI, "_take_zynpots")
    for i, d in ((0, 1), (0, 1), (3, -1)):
        hw.feed_pot(i, d)       # as zyncore's callback, summed until the GUI takes them
    ui._take_zynpots()
    assert screen.turns == [(0, 2), (3, -1)]
    ui._take_zynpots()
    assert screen.turns == [(0, 2), (3, -1)]
