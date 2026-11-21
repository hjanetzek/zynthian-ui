"""The Organelle's encoder and AUX button on the kits' knobs and switches
(zyngui.zynthian_organelle_data.OrganelleKeys, as zynthian_widget_organelle; used by the Qt UI)."""

from types import SimpleNamespace

import pytest

od = pytest.importorskip("zyngui.zynthian_organelle_data")


@pytest.fixture
def keys():
    log = []
    k = od.OrganelleKeys(lambda path, ms: log.append(("pulse", path, ms)),
                         lambda path, value: log.append(("send", path, value)),
                         lambda on: log.append(("select_mode", on)),
                         lambda on: log.append(("autolong", on)),
                         (19, 23, 12, 13))
    k.log = log
    return k


def layout(name):
    """zynthian_gui_config.check_wiring_layout for wiring layout name (it compares the start)"""
    return lambda names: any(name.startswith(n) for n in names)


def test_kit_switches():
    assert od.kit_switches(layout("V5")) == (19, 23, 12, 13)
    assert od.kit_switches(layout("V5_ZYNFACE")) == (19, 23, 12, 13)
    assert od.kit_switches(layout("Z2_V3")) == (15, 16, 13, 14)
    assert od.kit_switches(layout("TOUCH_ONLY")) == (None, None, None, None)


@pytest.mark.parametrize("name", ["MCP23017_ZynScreen", "MCP23017_ZynScreen_Zynaptik", "MCP23017_Zynaptik-3"])
def test_kit_switches_v4_kits_s3_s4(name):
    # V4-type kits: S3 select mode, S4 AUX (switches 6, 7), no LEDs
    assert od.kit_switches(layout(name)) == (6, 7, None, None)


@pytest.mark.parametrize("name", ["TOUCH_ONLY", "MCP23017_ZynScreen", "Z2_V3"])
def test_kit_switches_touch_keypad_v5_numbers(name):
    # The touch keypad sends the V5 numbers on any layout (zynthian_gui_config remaps the wiring)
    assert od.kit_switches(layout(name), "v5_keypad_left") == (19, 23, 12, 13)


def test_knob_3_scrolls_only_in_select_mode(keys):
    assert not keys.zynpot(3, 1)
    assert keys.switch(19, "S")             # enter: scroll once
    assert keys.log == [("select_mode", True), ("pulse", "/enc_down", 50)]
    keys.log.clear()
    assert keys.zynpot(3, 1) and keys.zynpot(3, -2)
    assert not keys.zynpot(2, 1)            # other knobs: their controllers
    assert keys.log == [("pulse", "/enc_down", 50), ("pulse", "/enc_up", 50)]


def test_switch_3_selects_and_leaves(keys):
    keys.switch(19, "S")
    keys.log.clear()
    assert not keys.switch(3, "B")
    assert keys.switch(3, "S")
    assert keys.log == [("pulse", "/enc_sel", 100), ("select_mode", False)]
    assert not keys.select_mode
    assert not keys.switch(3, "S")          # not in select mode: chain control's SELECT


def test_select_mode_switch_again_selects(keys):
    keys.switch(19, "P")                    # the push is taken, nothing happens
    keys.switch(19, "S")
    keys.log.clear()
    keys.switch(19, "B")
    assert keys.log == [("select_mode", False), ("pulse", "/enc_sel", 100)]


def test_no_selector_no_select_mode(keys):
    keys.selector = False
    assert not keys.switch(19, "S")
    assert not keys.select_mode


def test_arrows(keys):
    assert not keys.arrow(1)
    keys.switch(19, "S")
    keys.log.clear()
    assert keys.arrow(-1)
    assert keys.log == [("pulse", "/enc_up", 50)]


def test_aux_held(keys):
    assert keys.switch(23, "P")
    assert keys.switch(23, "L")             # released after a long press
    assert keys.log == [("autolong", False), ("send", "/aux", 1), ("autolong", True), ("send", "/aux", 0)]


def test_reset_releases(keys):
    keys.switch(19, "S")
    keys.switch(23, "P")
    keys.log.clear()
    keys.reset()
    assert keys.log == [("select_mode", False), ("autolong", True), ("send", "/aux", 0)]


def test_leds(keys):
    leds = list(range(20))
    calls = []
    wsl = SimpleNamespace(wscolor_active2="a2", wscolor_green="g",
                          set_led=lambda i, c: calls.append(("set", i, c)),
                          blink=lambda i, c: calls.append(("blink", i, c)))
    keys.update_wsleds(wsl, leds)
    keys.switch(19, "S")
    keys.switch(23, "P")
    keys.update_wsleds(wsl, leds)
    assert calls == [("set", 12, "a2"), ("set", 13, "a2"), ("blink", 12, "a2"), ("set", 13, "g")]


def test_sel_key_selects_in_select_mode(keys):
    assert not keys.select()                # not in select mode: chain control's SELECT
    keys.switch(19, "S")
    keys.log.clear()
    assert keys.select()
    assert keys.log == [("pulse", "/enc_sel", 100), ("select_mode", False)]


def test_labels(keys):
    assert keys.labels() == {19: "MENU", 23: "AUX"}
    keys.switch(19, "S")
    assert keys.labels() == {19: "SELECT", 23: "AUX"}
    keys.selector = False
    assert keys.labels() == {23: "AUX"}     # F3 keeps its own action
