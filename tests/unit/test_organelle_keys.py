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


def test_kit_switches():
    def layout(name):
        return lambda names: name in names
    assert od.kit_switches(layout("V5")) == (19, 23, 12, 13)
    assert od.kit_switches(layout("Z2")) == (15, 16, 13, 14)
    assert od.kit_switches(layout("MCP23017_ZYN")) == (5, 4, None, None)
    assert od.kit_switches(layout("DUMMIES")) == (None, None, None, None)


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
