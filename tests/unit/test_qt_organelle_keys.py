"""The Organelle widget's keys in the Qt UI through the real input paths, per layout: the touch
keypad (V5 switch numbers, ZynUI.pushSwitch), CUIAs (ZYNSWITCH / ZYNPOT / arrows / SELECT_ACTION /
V5_ZYNPOT_SWITCH through the CUIA thread) and a V4 kit's switches and encoders (HwInput's poll and
encoder callback); the OSC messages reach a fake Pd (a liblo server as the patch's OSC target).

ZynUI and ChainControl are stand-ins with their real methods bound (as test_qt_zynpot); the CUIA
thread (ZynUI._cuia_task, which times the switches) runs in a thread of its own as in the UI, its
hand-over to the GUI thread (_cuiaRequested) runs _run_cuia at once."""

import threading
import time
from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6.QtCore")
liblo = pytest.importorskip("pyliblo3")
ui_mod = pytest.importorskip("zynqt.ui")

from zyngui import zynthian_gui_config  # noqa: E402
from zyngui.zynthian_organelle_data import OrganelleKeys  # noqa: E402
from zynqt.hw_input import HwInput  # noqa: E402
from zynqt.models.organelle import OrganelleView  # noqa: E402
from zynqt.screens import control as control_mod  # noqa: E402
from tests.unit.test_qt_zynpot import bind, fake_ui  # noqa: E402

ZynUI = ui_mod.ZynUI


def custom(**actions):
    """A custom switch's UI actions (zynthian_gui_config.custom_switch_ui_actions entry)"""
    config = {k: "" for k in ("P", "S", "B", "L", "AP", "AS", "AB", "AL")}
    config.update(actions)
    return config


def v5_actions():
    """The v5 wiring profile's actions of the keys used here (custom switch NN = switch NN + 3)"""
    actions = [None] * 24
    actions[14 - 1] = custom(P="ARROW_UP")                            # switch 17: up
    actions[15 - 1] = custom(S="SELECT_ACTION S", B="SELECT_ACTION B")  # switch 18: SEL
    actions[16 - 1] = custom(S="PROGRAM_CHANGE 3", B="PROGRAM_CHANGE 3")  # switch 19: F3
    actions[18 - 1] = custom(P="ARROW_DOWN")                          # switch 21: down
    actions[20 - 1] = custom(S="PROGRAM_CHANGE 4", B="PROGRAM_CHANGE 4")  # switch 23: F4
    for k in range(4):                                                # switches 24-27: knob pushes
        actions[21 + k - 1] = custom(S=f"V5_ZYNPOT_SWITCH {k},S", B=f"V5_ZYNPOT_SWITCH {k},B",
                                     L=f"V5_ZYNPOT_SWITCH {k},L")
    return actions


def v4_actions():
    """zynthian_envars_V4.sh: S1-S4 (custom switches 1-4 = switches 4-7) program changes"""
    return [custom(S=f"PROGRAM_CHANGE {n}", B=f"PROGRAM_CHANGE {n + 4}") for n in range(1, 5)]


@pytest.fixture
def v5_keypad(monkeypatch):
    # The VMs and desktops: no kit (TOUCH_ONLY), the docked keypad with the v5 profile
    monkeypatch.setattr(zynthian_gui_config, "wiring_layout", "TOUCH_ONLY")
    monkeypatch.setattr(zynthian_gui_config, "touch_navigation", "v5_keypad_left")
    monkeypatch.setattr(zynthian_gui_config, "custom_switch_ui_actions", v5_actions())
    monkeypatch.setattr(zynthian_gui_config, "zynpot2switch", [24, 25, 26, 27], raising=False)


@pytest.fixture
def v5_kit(monkeypatch):
    monkeypatch.setattr(zynthian_gui_config, "wiring_layout", "V5")
    monkeypatch.setattr(zynthian_gui_config, "touch_navigation", "")
    monkeypatch.setattr(zynthian_gui_config, "custom_switch_ui_actions", v5_actions())
    monkeypatch.setattr(zynthian_gui_config, "zynpot2switch", [24, 25, 26, 27], raising=False)


@pytest.fixture
def v4_kit(monkeypatch):
    monkeypatch.setattr(zynthian_gui_config, "wiring_layout", "MCP23017_ZynScreen")
    monkeypatch.setattr(zynthian_gui_config, "touch_navigation", "")
    monkeypatch.setattr(zynthian_gui_config, "custom_switch_ui_actions", v4_actions())
    monkeypatch.setattr(zynthian_gui_config, "zynpot2switch", [0, 1, 2, 3], raising=False)


class FakePd:
    """The patch's OSC server: what the widget sends"""

    def __init__(self):
        self.server = liblo.Server()     # a free port
        self.server.add_method(None, None, lambda path, args: self.messages.append((path, args[0] if args else None)))
        self.messages = []

    def target(self):
        return liblo.Address("127.0.0.1", self.server.port, liblo.UDP)

    def wait(self, n, timeout=2.0):
        """The messages once there are n (the pulses' releases come after 50 / 100 ms)"""
        end = time.monotonic() + timeout
        while len(self.messages) < n and time.monotonic() < end:
            self.server.recv(20)
        time.sleep(0.15)
        while self.server.recv(0):
            pass
        return self.messages

    def take(self, n):
        msgs = list(self.wait(n))
        self.messages.clear()
        return msgs

    def pulses(self, n):
        """n encoder pulses (path 1, then 0 after 50 / 100 ms): their paths in the order pressed
        (quick pulses overlap: the releases come after the next presses)"""
        msgs = self.take(2 * n)
        presses = [path for path, v in msgs if v == 1]
        assert sorted(presses) == sorted(path for path, v in msgs if v == 0), msgs
        return presses

    def close(self):
        self.server.free()


@pytest.fixture
def pd():
    p = FakePd()
    yield p
    p.close()


ENC_DOWN, ENC_UP, ENC_SEL = "/enc_down", "/enc_up", "/enc_sel"


class Leds:
    """KeypadLeds' API for the screens' update_wsleds"""
    wscolor_active2 = "active2"
    wscolor_green = "green"

    def __init__(self):
        self.calls = []

    def set_led(self, i, color):
        self.calls.append(("set", i, color))

    def blink(self, i, color):
        self.calls.append(("blink", i, color))


def setup(pd, selector=True):
    """ZynUI and ChainControl (the Organelle widget shown) stand-ins wired as in the UI"""
    ctrls = [SimpleNamespace(index=n, zctrl=object(), zctrls=[], nudged=[]) for n in range(4)]
    for c in ctrls:
        c.set_zctrl = c.zctrls.append
        c.nudge_fine = lambda d, fine, c=c: c.nudged.append(d)
    cc = SimpleNamespace(_widget_type="organelle", _mode="control", controllers=ctrls, isChain=True,
                         midi_learning=0, _organelle_selector=None, _page_zctrls=[], modes=[], learned=[])
    cc.set_mode = cc.modes.append
    cc.toggle_midi_learn = cc.learned.append
    bind(cc, control_mod.ChainControl, "switch", "zynpot", "switch_select", "cuia_v5_zynpot_switch",
         "cuia_arrow_up", "cuia_arrow_down", "_sl_alt", "_knob_controller", "_organelle_select_mode",
         "_autolong", "update_wsleds", "fkey_labels")
    view = OrganelleView()
    view.osc_target = pd.target()
    cc.organelle_view = view
    cc.organelle_keys = OrganelleKeys(view.pulse, view.send, cc._organelle_select_mode, cc._autolong,
                                      control_mod.organelle_kit_switches())
    cc.organelle_keys.selector = selector
    view.select_hook = cc.organelle_keys.select

    ui = fake_ui(cc, current="chain_control")
    ui.alt_mode = False
    ui.program_changes = []
    ui.keypad_leds = Leds()
    ui.cuia_program_change = ui.program_changes.append
    ui._switch_timing = ZynUI._switch_timing
    ui.state_manager.parse_cuia_params = lambda s: [int(p) if p.strip().isdigit() else p.strip() for p in s.split(",")]
    ui._cuiaRequested = SimpleNamespace(emit=lambda name, params: ui._run_cuia(name, list(params)))
    bind(ui, ZynUI, "_push_action", "cuia__zynswitch", "zynswitch", "_is_current_screen_switch", "get_current_screen",
         "switch_select", "cuia_select_action", "cuia_v5_zynpot_switch", "cuia_arrow_up", "cuia_arrow_down",
         "pushSwitch",
         "zynswitch_disable_autolong", "zynswitch_enable_autolong", "_switch_zynpot", "_take_zynpots")
    cc.ui = ui
    return ui, cc


class CuiaThread:
    """ZynUI's CUIA thread over ui.cuia_queue; wait() returns once the events queued so far are
    handled (a marker CUIA behind them)"""

    def __init__(self, ui):
        self.ui = ui
        self.done = threading.Event()
        ui.cuia__mark = lambda params: self.done.set()
        self.thread = threading.Thread(target=ui._cuia_task, daemon=True)
        self.thread.start()

    def wait(self):
        self.done.clear()
        self.ui.cuia_queue.put_nowait(("_MARK", None))
        assert self.done.wait(5)

    def stop(self):
        self.ui.cuia_queue.put_nowait("__EXIT__")
        self.thread.join(5)


@pytest.fixture
def run(pd):
    """setup() with the CUIA thread running"""
    threads = []

    def start(selector=True):
        ui, cc = setup(pd, selector)
        ui.cuia = CuiaThread(ui)
        threads.append(ui.cuia)
        return ui, cc
    yield start
    for t in threads:
        t.stop()


def keypad(ui, *keys):
    """Taps on the keypad (key k: switch k + 4, pressed and released), through the CUIA thread"""
    for k in keys:
        ui.pushSwitch(k, True)
        ui.pushSwitch(k, False)
    ui.cuia.wait()


def osc(ui, *events):
    """OSC CUIAs (path, args) through the CUIA thread"""
    for path, args in events:
        ui.cuia_queue.put_nowait((path, args, "osc"))
    ui.cuia.wait()


# V5 numbers: the touch keypad (any layout) and a V5 kit

F3, F4, UP, SEL, DOWN = 15, 19, 13, 14, 17      # keypad keys (switches 19, 23, 17, 18, 21)


def test_keypad_f3_select_mode_arrows_scroll_f3_selects(v5_keypad, pd, run):
    ui, cc = run()
    keys = cc.organelle_keys
    assert (keys.switch_selmode, keys.switch_aux, keys.led_selmode, keys.led_aux) == (19, 23, 12, 13)
    keypad(ui, F3)
    assert keys.select_mode and cc.organelle_view.selectMode
    assert cc.controllers[3].zctrls[-1].symbol == "Select"   # knob 4 shows the selector
    assert pd.pulses(1) == [ENC_DOWN]                           # entering scrolls once (Tk)
    keypad(ui, DOWN, DOWN, UP)
    assert pd.pulses(3) == [ENC_DOWN, ENC_DOWN, ENC_UP]
    keypad(ui, F3)                                          # again: select, the mode ends
    assert not keys.select_mode
    assert pd.pulses(1) == [ENC_SEL]
    assert ui.program_changes == []                         # F3 didn't run its PROG 3


def test_keypad_sel_selects_in_select_mode_else_chain_control(v5_keypad, pd, run):
    ui, cc = run()
    keypad(ui, SEL)
    assert cc.modes == ["select"] and pd.take(0) == []      # SELECT: chain control's select mode
    cc.modes.clear()
    keypad(ui, F3)
    pd.take(2)
    keypad(ui, SEL)
    assert cc.modes == [] and not cc.organelle_keys.select_mode
    assert pd.pulses(1) == [ENC_SEL]


def test_keypad_arrows_outside_select_mode_navigate(v5_keypad, pd, run):
    ui, cc = run()
    keypad(ui, DOWN)
    assert ui.navigated == ["down"] and pd.take(0) == []


def test_keypad_f4_is_aux_held_without_long_press(v5_keypad, pd, run, monkeypatch):
    monkeypatch.setattr(zynthian_gui_config, "zynswitch_long_seconds", 0.05)
    ui, cc = run()
    ui.pushSwitch(F4, True)
    ui.cuia.wait()
    assert ui.zynswitch_autolong_disabled and cc.organelle_view.aux
    assert pd.take(1) == [("/aux", 1)]
    time.sleep(0.4)                                         # held past the long press time:
    ui.cuia.wait()
    assert cc.organelle_view.aux                            # no long press released it
    ui.pushSwitch(F4, False)
    ui.cuia.wait()
    assert not ui.zynswitch_autolong_disabled and not cc.organelle_view.aux
    assert pd.take(1) == [("/aux", 0)]
    assert ui.program_changes == []


def test_keypad_without_selector_f3_keeps_its_action(v5_keypad, pd, run):
    ui, cc = run(selector=False)
    keypad(ui, F3)
    assert ui.program_changes == [[3]] and not cc.organelle_keys.select_mode
    assert cc.fkey_labels() == {23: "AUX"}


def test_keypad_leds_and_labels(v5_keypad, pd, run):
    ui, cc = run()
    leds = list(range(20))
    assert cc.fkey_labels() == {19: "MENU", 23: "AUX"}
    cc.update_wsleds(leds)
    keypad(ui, F3)
    ui.pushSwitch(F4, True)
    ui.cuia.wait()
    cc.update_wsleds(leds)
    assert ui.keypad_leds.calls == [("set", 12, "active2"), ("set", 13, "active2"),
                                    ("blink", 12, "active2"), ("set", 13, "green")]
    assert cc.fkey_labels() == {19: "SELECT", 23: "AUX"}


def test_v5_cuias_zynswitch_and_knob_4(v5_kit, pd, run):
    # ZYNSWITCH with the V5 numbers (OSC, websocket), knob 4 turned (ZYNPOT) and pushed (switch 27)
    ui, cc = run()
    osc(ui, ("ZYNSWITCH", (19, "P")), ("ZYNSWITCH", (19, "R")))
    assert cc.organelle_keys.select_mode
    pd.take(2)
    osc(ui, ("ZYNPOT", (3, 1)), ("ZYNPOT", (3, -1)), ("ARROW_DOWN", None))
    assert pd.pulses(3) == [ENC_DOWN, ENC_UP, ENC_DOWN]
    assert cc.controllers[3].nudged == []                   # knob 4 doesn't turn its controller
    osc(ui, ("ZYNSWITCH", (27, "P")), ("ZYNSWITCH", (27, "R")))
    assert not cc.organelle_keys.select_mode and cc.learned == []
    assert pd.pulses(1) == [ENC_SEL]
    osc(ui, ("ZYNSWITCH", (23, "P")), ("ZYNSWITCH", (23, "R")))
    assert pd.take(2) == [("/aux", 1), ("/aux", 0)]


def test_v5_short_and_bold_given_by_osc(v5_kit, pd, run):
    ui, cc = run()
    osc(ui, ("ZYNSWITCH", (19, "S")))
    assert cc.organelle_keys.select_mode
    osc(ui, ("ZYNSWITCH", (19, "B")))
    assert not cc.organelle_keys.select_mode
    assert pd.pulses(2) == [ENC_DOWN, ENC_SEL]


# V4 kit: S1-S4 are switches 4-7, the knob pushes 0-3, the knobs zynpots 0-3

def test_v4_cuias_s3_s4_and_knob_4(v4_kit, pd, run):
    ui, cc = run()
    keys = cc.organelle_keys
    assert (keys.switch_selmode, keys.switch_aux, keys.led_selmode, keys.led_aux) == (6, 7, None, None)
    osc(ui, ("ZYNSWITCH", (6, "P")), ("ZYNSWITCH", (6, "R")))       # S3
    assert keys.select_mode and pd.pulses(1) == [ENC_DOWN]
    osc(ui, ("ZYNPOT", (3, 1)), ("ZYNPOT", (3, 1)))                 # knob 4
    assert pd.pulses(2) == [ENC_DOWN, ENC_DOWN]
    osc(ui, ("ZYNSWITCH", (3, "P")), ("ZYNSWITCH", (3, "R")))       # knob 4's push: select
    assert not keys.select_mode and pd.pulses(1) == [ENC_SEL]
    osc(ui, ("ZYNSWITCH", (7, "P")))                                # S4 held
    assert pd.take(1) == [("/aux", 1)] and ui.zynswitch_autolong_disabled
    osc(ui, ("ZYNSWITCH", (7, "R")))
    assert pd.take(1) == [("/aux", 0)] and not ui.zynswitch_autolong_disabled
    assert ui.program_changes == []                                 # S3 / S4's program changes not run
    osc(ui, ("ZYNSWITCH", (4, "P")), ("ZYNSWITCH", (4, "R")))       # S1 keeps its action
    assert ui.program_changes == [[1]]


def test_v4_kit_hardware(v4_kit, pd, run):
    # The kit itself: HwInput polls zyncore's switches (0 pushed, then the duration in µs) and
    # sums the encoder callback's deltas
    ui, cc = run()
    script = {}

    def get_zynswitch(i, long_us):
        return script.pop(i, -1)
    lib = SimpleNamespace(get_zynswitch=get_zynswitch)
    hw = HwInput(lib, 7, 4, ui.cuia_queue.put_nowait, ZynUI._has_switch_ui_action)
    ui.hw_input = hw

    def press(i, us=100000):
        script[i] = 0
        hw.poll_switches()
        script[i] = us
        hw.poll_switches()
        ui.cuia.wait()

    press(6)                                                # S3
    assert cc.organelle_keys.select_mode and pd.pulses(1) == [ENC_DOWN]
    hw.feed_pot(3, 1)
    hw.feed_pot(3, 1)                                       # summed: one turn of 2
    ui._take_zynpots()
    hw.feed_pot(3, -1)
    ui._take_zynpots()
    assert pd.pulses(2) == [ENC_DOWN, ENC_UP]
    press(3)                                                # knob 4's push
    assert not cc.organelle_keys.select_mode and pd.pulses(1) == [ENC_SEL]
    script[7] = 0                                           # S4 held ...
    hw.poll_switches()
    ui.cuia.wait()
    assert pd.take(1) == [("/aux", 1)]
    script[7] = 3000000                                     # ... 3 s: no long press action
    hw.poll_switches()
    ui.cuia.wait()
    assert pd.take(1) == [("/aux", 0)] and ui.program_changes == []


def test_on_screen_sel_in_select_mode_ends_it(v4_kit, pd, run):
    ui, cc = run()
    view = cc.organelle_view
    view.encoderPress()                                     # not in select mode: a plain push
    assert pd.pulses(1) == [ENC_SEL]
    osc(ui, ("ZYNSWITCH", (6, "S")))
    pd.take(2)
    view.encoder(1)
    assert pd.pulses(1) == [ENC_DOWN]
    view.encoderPress()
    assert not cc.organelle_keys.select_mode and pd.pulses(1) == [ENC_SEL]


@pytest.mark.parametrize("layout, touch, expected", [
    ("TOUCH_ONLY", "", (None, None, None, None)),
    ("TOUCH_ONLY", "v5_keypad_left", (19, 23, 12, 13)),
    ("V5", "", (19, 23, 12, 13)),
    ("MCP23017_ZynScreen", "", (6, 7, None, None)),
    ("MCP23017_ZynScreen", "v5_keypad_right", (19, 23, 12, 13)),
    ("Z2_V3", "", (15, 16, 13, 14)),
])
def test_switches_per_layout(monkeypatch, layout, touch, expected):
    monkeypatch.setattr(zynthian_gui_config, "wiring_layout", layout)
    monkeypatch.setattr(zynthian_gui_config, "touch_navigation", touch)
    assert control_mod.organelle_kit_switches() == expected
