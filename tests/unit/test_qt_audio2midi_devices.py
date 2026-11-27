"""The Qt MIDI devices list and the audio to MIDI converter as upstream designs it since 34b22105 /
acee218e: each converter output is a MIDI input device (tap: its options, as any device); a long
press (Tk: bold select) shows the controls of its channel (SCREEN_AUDIO2MIDI with the channel),
the output's options offer them too. No converter toggle, no "Select audio inputs" any more (each
channel has an audio input controller)."""

from types import SimpleNamespace

import pytest

routing = pytest.importorskip("zynqt.screens.routing")
zynautoconnect = pytest.importorskip("zynautoconnect")


class FakeUI:
    def __init__(self):
        self.a2m = []
        self.options = None
        self.state_manager = SimpleNamespace(ctrldev_manager=None)

    def cuia_screen_audio2midi(self, params=None):
        self.a2m.append(params)

    def show_options(self, title, opts):
        self.options = (title, opts)


def test_long_press_on_a_converter_output_shows_its_channel_controls():
    ui = FakeUI()
    uid = zynautoconnect.AUDIO2MIDI_UIDS[1]
    screen = SimpleNamespace(ui=ui, midi_input=True, entries=[{"data": (uid, 7, "Audio ➔ MIDI 2")}])
    routing.MidiDevices.select_action(screen, 0, "B")   # a QObject: on a stand-in
    assert ui.a2m == [[2]]


def test_converter_output_options_offer_its_channel_controls(monkeypatch):
    ui = FakeUI()
    uid = zynautoconnect.AUDIO2MIDI_UIDS[0]
    port = SimpleNamespace(aliases=[uid, "Audio ➔ MIDI 1"])
    monkeypatch.setattr(zynautoconnect, "devices_in", [None, port])
    for name, value in (("get_midi_in_dev_mode", 1), ("get_zynseq_exclude_ports", []), ("get_ext_clock_zmip", -1)):
        monkeypatch.setattr(zynautoconnect, name, lambda *a, v=value: v)
    monkeypatch.setattr(routing, "device_drivers", lambda sm, idev: [])
    routing.show_device_options(ui, True, 1, lambda: None)
    title, opts = ui.options
    labels = [o[0] for o in opts]
    assert labels[0] == "Audio ➔ MIDI controls"
    assert "Select audio inputs" not in labels
    opts[0][1]()
    assert ui.a2m == [[1]]
