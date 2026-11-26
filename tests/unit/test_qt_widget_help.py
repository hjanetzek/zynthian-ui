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
    ui = SimpleNamespace(current_screen="chain_control", list_screens={},
                         current_processor=SimpleNamespace(name="KR-106", engine=engine))
    ui._widget_help_paths = ZynUI._widget_help_paths.__get__(ui)
    return ui


def test_widget_help_page_first(tmp_path):
    page = tmp_path / "zynthian_widget_kr106_gui.html"
    page.write_text("<h1>KR-106</h1>")
    assert ZynUI._help_topic(topic_ui(str(page))) == [str(page), "kr-106.html", "chain_control.html"]


@pytest.mark.parametrize("fpath", [None, "", "/nonexistent/widget_help.html"])
def test_without_widget_help(fpath):
    assert ZynUI._help_topic(topic_ui(fpath)) == ["kr-106.html", "chain_control.html"]


def test_show_help_opens_the_widget_page_by_its_absolute_path(tmp_path, monkeypatch):
    """zynthian_help.find_file takes a leading "/" as the help directory: the widget's page (an
    absolute path in its bundle) is opened as it is"""
    page = tmp_path / "zynthian_widget_kr106_gui.html"
    page.write_text("<h1>KR-106</h1>")
    ui = topic_ui(str(page))
    ui._help_topic = ZynUI._help_topic.__get__(ui)
    shown = []
    ui._show_help_page = shown.append
    ui._show_help_index = lambda: shown.append("index")
    monkeypatch.setattr(ui_mod.zynthian_gui_config, "layout", {"name": "V5"}, raising=False)
    ZynUI.show_help.__wrapped__(ui)   # (without the gui_thread wrapper)
    assert shown == [str(page)]
