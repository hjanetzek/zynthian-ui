"""The Qt screens follow upstream's cursor fixes of the Tk screens:
- ZS3 list (7d445b81): the cursor starts on the last loaded ZS3 whatever row the last visit left;
- pattern editor (f4c0f2061): the cursor row is centred in the rows shown at the pattern's zoom."""

from types import SimpleNamespace

import pytest

zs3_mod = pytest.importorskip("zynqt.screens.zs3")
pated_mod = pytest.importorskip("zynqt.screens.pattern_editor")


def test_zs3_build_resets_the_cursor_before_filling():
    seen = []
    screen = SimpleNamespace(_index=3)
    screen.fill = lambda: seen.append(screen._index)
    zs3_mod.ZS3.build(screen)   # a QObject: build() on a stand-in
    # fill() then places the cursor on the last loaded ZS3 (its "first row" rule)
    assert seen == [0]


def view_rows(grid_height, zoom, n_rows=128):
    pe = SimpleNamespace(_grid_height=grid_height, keymap=[{}] * n_rows)
    return pated_mod.PatternEditor._view_rows_at(pe, zoom)


def test_pattern_view_rows_follow_the_zoom():
    # PatternEditorView.qml: rowHeight = clamp(gh // 16 + zoom, gh // min(36, rows), gh // 6)
    assert view_rows(320, 0) == 16
    assert view_rows(320, 20) == 8          # rows of 40 px
    assert view_rows(320, 1000) == 6        # at most gh // 6 px high
    assert view_rows(320, -1000) == 40      # at least gh // 36 px high (8 px)
    assert view_rows(320, -1000, n_rows=12) == 12   # few rows: at least gh // 12 px high


def test_pattern_view_rows_unknown_without_a_grid():
    assert view_rows(0, 5) == 0
