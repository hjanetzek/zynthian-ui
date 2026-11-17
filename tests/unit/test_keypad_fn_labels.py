"""The Qt keypad's F-key function labels (zynqt.keypad_leds): short CUIA labels and the custom
switch action a key press runs."""

import pytest

keypad_leds = pytest.importorskip("zynqt.keypad_leds")
cuia_label = keypad_leds.cuia_label
switch_cuia = keypad_leds.switch_cuia

V5_F1 = {"P": "", "S": "PROGRAM_CHANGE 1", "B": "PROGRAM_CHANGE 1", "L": "",
         "AP": "", "AS": "PROGRAM_CHANGE 5", "AB": "PROGRAM_CHANGE 5", "AL": ""}


@pytest.mark.parametrize("cuia, label", [
    ("PROGRAM_CHANGE 1", "PROG 1"),
    ("ZS3_LOAD 3", "ZS3 3"),
    ("TOGGLE_AUDIO_RECORD", "AUD REC"),
    ("SHOW_SCREEN mixer", "MIXER"),
    ("START_MIDI_RECORD", "START\nMIDI REC"),
    ("NOP", ""),
    ("", ""),
    (None, ""),
])
def test_cuia_label(cuia, label):
    assert cuia_label(cuia) == label


def test_labels_stay_short():
    for cuia in ("WORKFLOW_CAPTURE_START", "ZYNAPTIK_CVOUT_SET_VOLTS_OCTAVE 1,2", "RELOAD_MIDI_CONFIG"):
        lines = cuia_label(cuia).split("\n")
        assert len(lines) <= 2 and all(len(x) <= keypad_leds.LINE_LEN for x in lines)


def test_switch_cuia_alt_and_fallbacks():
    assert switch_cuia(V5_F1, False) == "PROGRAM_CHANGE 1"
    assert switch_cuia(V5_F1, True) == "PROGRAM_CHANGE 5"
    # A short press with ALT and no ALT action runs the plain one (zynqt.ui.cuia__zynswitch)
    assert switch_cuia(dict(V5_F1, AS=""), True) == "PROGRAM_CHANGE 1"
    assert switch_cuia({"S": "", "B": "SCREEN_ZS3"}, False) == "SCREEN_ZS3"
    assert switch_cuia({"P": "ARROW_UP", "AP": ""}, True) == "ARROW_UP"
    assert switch_cuia(None, False) == ""
