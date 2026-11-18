"""The Qt MIDI recorder screen's title follows the Tk screen: "MIDI Player" since upstream
14c9ddad (the screen mainly plays MIDI files)."""

from types import SimpleNamespace

import pytest

screen_mod = pytest.importorskip("zynqt.screens.midi_recorder")


def test_title_is_midi_player(monkeypatch):
    monkeypatch.setattr(screen_mod, "midi_file_rows", lambda *a: [])
    titles = []
    screen = SimpleNamespace(state_manager=SimpleNamespace(status_midi_recorder=False, status_midi_player=False),
                             set_title=titles.append, set_entries=lambda entries: None, toggle_loop=None)
    screen_mod.MidiRecorder.fill(screen)   # a QObject: fill() on a stand-in, no Qt objects needed
    assert titles == ["MIDI Player"]
