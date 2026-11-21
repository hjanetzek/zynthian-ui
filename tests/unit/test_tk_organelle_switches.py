"""The Tk Organelle widget's switches (zynthian_widget_organelle.switch): the push (P) of the select
mode and AUX switches must not be taken. zynthian_gui's CUIA thread treats a push its screen takes
as a push action (zynswitch_push True: auto-repeated while held, the release dropped), so the
touch keypad's and the ZYNSWITCH CUIA's P / R never toggled the select mode and never released
AUX."""

import pytest

wo = pytest.importorskip("zyngui.zynthian_widget_organelle")


class FakeLiblo:
    def __init__(self):
        self.sent = []

    def send(self, target, path, value):
        self.sent.append((path, value))


@pytest.fixture
def widget(monkeypatch):
    liblo = FakeLiblo()
    monkeypatch.setattr(wo, "liblo", liblo)
    w = wo.zynthian_widget_organelle.__new__(wo.zynthian_widget_organelle)
    w.osc_target = "pd"
    w.selector = True
    w.select_mode = False
    w.aux_pushed = False
    w.switch_i_selmode, w.switch_i_aux = 19, 23
    w.modes = []
    w.set_select_mode = lambda sm=True: (w.modes.append(sm), setattr(w, "select_mode", sm))
    w.after = lambda ms, func: func()
    autolong = []
    w.zyngui = type("ZynGui", (), {"zynswitch_disable_autolong": lambda self: autolong.append(False),
                                   "zynswitch_enable_autolong": lambda self: autolong.append(True)})()
    w.liblo, w.autolong = liblo, autolong
    return w


def test_select_mode_push_not_taken_release_toggles(widget):
    assert not widget.switch(19, "P")
    assert widget.switch(19, "S")
    assert widget.modes == [True]
    assert widget.liblo.sent == [("/enc_down", 1), ("/enc_down", 0)]


def test_aux_push_sent_but_not_taken_release_comes_back(widget):
    assert not widget.switch(23, "P")
    assert widget.aux_pushed and widget.autolong == [False]
    assert widget.switch(23, "L")          # released after a long hold
    assert not widget.aux_pushed and widget.autolong == [False, True]
    assert widget.liblo.sent == [("/aux", 1), ("/aux", 0)]
