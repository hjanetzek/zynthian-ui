"""The Qt help on chain control shows the help page a processor's widget declares (zyngui:help in
the widget's LV2 data: engine.custom_gui_help_fpath), as Tk's zynthian_gui_control.get_help_fpath;
without one (or when the file is gone) the processor's and chain control's pages as before."""

from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6.QtCore")
ui_mod = pytest.importorskip("zynqt.ui")

ZynUI = ui_mod.ZynUI


def topic_ui(help_fpath):
    engine = SimpleNamespace(custom_gui_help_fpath=help_fpath)
    return SimpleNamespace(current_screen="chain_control", list_screens={},
                           current_processor=SimpleNamespace(name="KR-106", engine=engine))


def test_widget_help_page_first(tmp_path):
    page = tmp_path / "zynthian_widget_kr106_gui.html"
    page.write_text("<h1>KR-106</h1>")
    assert ZynUI._help_topic(topic_ui(str(page))) == [str(page), "kr-106.html", "chain_control.html"]


@pytest.mark.parametrize("fpath", [None, "", "/nonexistent/widget_help.html"])
def test_without_widget_help(fpath):
    assert ZynUI._help_topic(topic_ui(fpath)) == ["kr-106.html", "chain_control.html"]
