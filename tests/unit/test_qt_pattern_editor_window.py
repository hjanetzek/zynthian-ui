"""The pattern editor shows a controller's window (DrivenByMoss' ClipEditWindow,
docs/controller-view-sync.md): beats to steps, notes to keymap rows, kept per pattern, the
cursor moved into it, and the PATTERN_EDITOR_WINDOW CUIA."""

from types import SimpleNamespace

import pytest

QtCore = pytest.importorskip("PySide6.QtCore")
pated_mod = pytest.importorskip("zynqt.screens.pattern_editor")
ui_mod = pytest.importorskip("zynqt.ui")


class Libseq:
    def __init__(self, steps=32, spb=4):
        self.steps, self.spb = steps, spb

    def getSteps(self):
        return self.steps

    def getStepsPerBeat(self):
        return self.spb


@pytest.fixture
def editor():
    app = QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])
    libseq = Libseq()
    ui = SimpleNamespace(state_manager=SimpleNamespace(zynseq=SimpleNamespace(libseq=libseq)))
    pe = pated_mod.PatternEditor(ui)
    pe._shown = True
    pe.pattern = 7
    pe.keymap = [{"note": n} for n in range(128)]
    pe.cursor = [0, 70]
    pe._app = app
    return pe


def test_window_in_steps_and_rows(editor):
    seen = []
    editor.windowChanged.connect(lambda: seen.append(editor.viewWindow))
    # The JAM's second page of 8 1/16 steps (2 beats from beat 2), C3..C4
    editor.show_window(2.0, 2.0, 48, 60, 7)
    assert seen == [[8, 8, 48, 60]]
    # The cursor moves into the window: the first step, the lowest row
    assert editor.cursor == [8, 48]
    # A cursor in the window stays
    editor.cursor = [10, 50]
    editor.show_window(2.0, 2.0, 48, 60, 7)
    assert editor.cursor == [10, 50]


def test_window_clamped_to_the_pattern(editor):
    editor.show_window(16.0, 4.0, 60, 67, 7)   # beyond the 32 steps
    assert editor.viewWindow == [31, 1, 60, 67]


def test_window_of_another_pattern_waits(editor):
    seen = []
    editor.windowChanged.connect(lambda: seen.append(1))
    editor.show_window(0.0, 4.0, 36, 51, 9)
    assert seen == [] and editor.viewWindow == []
    editor.pattern = 9     # load() of that pattern shows it
    assert editor.viewWindow == [0, 16, 36, 51]


def test_window_on_a_drum_map(editor):
    editor.keymap = [{"note": n} for n in (36, 38, 42, 46, 49)]
    editor.show_window(0.0, 2.0, 37, 43, 7)
    assert editor.viewWindow == [0, 8, 1, 2]
    # No note of the map in the range: the nearest row
    editor.show_window(0.0, 2.0, 60, 70, 7)
    assert editor.viewWindow == [0, 8, 4, 4]


def test_window_ignores_nonsense(editor):
    editor.show_window(0.0, 0.0, 48, 60, 7)
    editor.show_window(0.0, 1.0, 60, 48, 7)
    assert editor.viewWindow == []


def test_cuia_parses_its_parameters():
    calls = []
    ui = SimpleNamespace(pattern_editor=SimpleNamespace(show_window=lambda *a: calls.append(a)))
    ui_mod.ZynUI.cuia_pattern_editor_window(ui, ["1.5", "2", "48", "60", "3"])
    ui_mod.ZynUI.cuia_pattern_editor_window(ui, [0, 4, 36, 51])
    ui_mod.ZynUI.cuia_pattern_editor_window(ui, [0, 4])   # too few: ignored
    assert calls == [(1.5, 2.0, 48, 60, 3), (0.0, 4.0, 36, 51, None)]
