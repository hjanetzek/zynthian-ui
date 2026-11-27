"""The Qt UI's CUIA thread (ZynUI._cuia_task) with malformed events: ZYNSWITCH (as ZYNPOT before
it, test_qt_zynpot) and the queue entries themselves are parsed with guards, so bad arguments are
logged and skipped and the thread goes on; the websocket input accepts what the thread accepts
(ws_cuia_args_ok)."""

import pytest

pytest.importorskip("PySide6.QtCore")
ui_mod = pytest.importorskip("zynqt.ui")

from tests.unit.test_qt_zynpot import bind, fake_ui, run_queue  # noqa: E402

ZynUI = ui_mod.ZynUI


def switch_ui():
    ui = fake_ui()
    bind(ui, ZynUI, "_push_action")
    ui._switch_timing = ZynUI._switch_timing
    ui.alt_mode = False
    return ui


@pytest.mark.parametrize("event", [
    ("ZYNSWITCH", (1, "S"), "osc"),
    ("ZYNSWITCH", ("1", "s"), "osc"),
    ("ZYNSWITCH", ("1.0", "S"), "osc"),
    ("ZYNSWITCH", (1.0, "S"), "osc"),
    "zynswitch 1,S",
])
def test_zynswitch_numbers_or_strings(event):
    assert run_queue(switch_ui(), event) == [("_zynswitch", [1, "S"])]


def test_zynswitch_release_with_duration():
    # The kit's switches: P, then R with zyncore's duration in µs (here: bold)
    from zyngui import zynthian_gui_config
    us = int(1000000 * (zynthian_gui_config.zynswitch_bold_seconds + zynthian_gui_config.zynswitch_long_seconds) / 2)
    emitted = run_queue(switch_ui(), ("ZYNSWITCH", ("1", "P")), ("ZYNSWITCH", ("1", "R", str(us))))
    assert emitted == [("_zynswitch", [1, "B"])]


@pytest.mark.parametrize("params", [(), ("1",), ("x", "S"), (None, "S"), ("inf", "S"), ("1", "R", "soon"),
                                    ("nan", "S")])
def test_zynswitch_bad_parameters_skipped_thread_goes_on(params):
    ui = switch_ui()
    emitted = run_queue(ui, ("ZYNSWITCH", params, "osc"), ("ZYNSWITCH", ("2", "S"), "osc"))
    assert emitted == [("_zynswitch", [2, "S"])]


def test_zynswitch_release_with_bad_duration_after_press():
    ui = switch_ui()
    emitted = run_queue(ui, ("ZYNSWITCH", ("1", "P")), ("ZYNSWITCH", ("1", "R", "x")), ("ZYNSWITCH", ("1", "R")))
    assert emitted == [("_zynswitch", [1, "S"])]


def test_zynpot_overflow_skipped():
    # float("inf") converts, int() of it raises OverflowError (not ValueError)
    emitted = run_queue(switch_ui(), ("ZYNPOT", ("inf", "1"), "osc"), ("ZYNPOT", ("1", "-inf"), "osc"),
                        ("ZYNPOT", ("0", "1"), "osc"))
    assert emitted == [("_zynpot", [0, 1])]


@pytest.mark.parametrize("event", [(None, (1,)), (5,), (), ("",), 7])
def test_bad_events_skipped_thread_goes_on(event):
    emitted = run_queue(switch_ui(), event, ("ARROW_DOWN", None))
    assert emitted == [("ARROW_DOWN", [])]


@pytest.mark.parametrize("event,expected", [
    ("SELECT 4", ("SELECT", ["4"])),
    ("SELECT", ("SELECT", [])),
    (("SELECT", 4), ("SELECT", [4])),           # one value, not a list (drivers)
    (("SELECT", (4,), "osc"), ("SELECT", [4])),
    (("SELECT", "B"), ("SELECT", ["B"])),       # a string is one parameter, not its characters
    (("BACK",), ("BACK", [])),
    (("BACK", None), ("BACK", [])),
])
def test_cuia_event(event, expected):
    assert ui_mod.cuia_event(event) == expected


def test_websocket_accepts_what_the_thread_accepts():
    ok = ui_mod.ws_cuia_args_ok
    for args in (["3", "1.0"], [3.0, -1], ["3", "1", "P"]):
        assert ok("ZYNPOT", args) and ui_mod.zynpot_params(args) is not None
    for args in (["1.0", "S"], [1, "R", "200000.0"], ["2", "b"]):
        assert ok("ZYNSWITCH", args) and ui_mod.zynswitch_params(args) is not None
    for args in ([], ["3"], ["x", 1], ["inf", 1]):
        assert not ok("ZYNPOT", args) and ui_mod.zynpot_params(args, log=False) is None
    for args in ([], ["1"], ["a", "S"], [1, "R", "soon"]):
        assert not ok("zynswitch", args) and ui_mod.zynswitch_params(args, log=False) is None
    assert ok("ARROW_DOWN", []) and ok("SELECT", ["x"])


def test_an_error_in_one_event_doesnt_end_the_thread():
    ui = switch_ui()
    calls = []

    def broken(i):
        calls.append(i)
        if len(calls) == 1:
            raise RuntimeError("wiring changed under us")
        return None
    ui._switch_zynpot = broken
    emitted = run_queue(ui, ("ZYNSWITCH", ("1", "S")), ("ZYNSWITCH", ("2", "S")))
    assert emitted == [("_zynswitch", [2, "S"])]


# Upstream #1687 (35fdbbb2): a switch pressed in power save wakes the UI; its push and short
# actions are ignored, bold and long still act

def sleeping_ui():
    ui = switch_ui()
    ui.state_manager.power_save_mode = True
    return ui


def test_short_press_in_power_save_only_wakes():
    ui = sleeping_ui()
    emitted = run_queue(ui, ("ZYNSWITCH", ("1", "P")), ("ZYNSWITCH", ("1", "R", "1000")))
    assert emitted == []


def test_bold_press_in_power_save_still_acts():
    from zyngui import zynthian_gui_config
    us = int(1000000 * (zynthian_gui_config.zynswitch_bold_seconds + zynthian_gui_config.zynswitch_long_seconds) / 2)
    ui = sleeping_ui()
    emitted = run_queue(ui, ("ZYNSWITCH", ("1", "P")), ("ZYNSWITCH", ("1", "R", str(us))))
    assert emitted == [("_zynswitch", [1, "B"])]


def test_release_after_waking_is_still_a_wake_press():
    """The UI wakes after the press (every CUIA sets the event flag, the power save check ends
    power save on its next tick: here before the release); the release still belongs to the
    waking press, the next press acts again"""
    ui = sleeping_ui()
    sm = ui.state_manager
    flags = []

    def set_event_flag():
        if flags:
            sm.power_save_mode = False   # the check ran after the press
        flags.append(True)

    sm.set_event_flag = set_event_flag
    emitted = run_queue(ui, ("ZYNSWITCH", ("2", "P")), ("ZYNSWITCH", ("2", "R", "1000")), ("ZYNSWITCH", ("2", "S")))
    assert emitted == [("_zynswitch", [2, "S"])]
