"""Qt chain control: a widget follows its processor when the processor is reloaded
(chain_manager.reload_processor: a new object with the same id, the old one leaves its chain).

Upstream 6435cee7 fixed this in the Tk control screen (refresh_widget_processor): a Tk widget
instance shown again without show_widget kept polling the stopped engine. The Qt screen sets its
widget views on every build (_set_widget rebinds a view whose processor is another object), and
it builds on show and on chainsChanged while shown."""

import pytest

pytest.importorskip("PySide6.QtCore")
pytest.importorskip("zynqt.ui")

from tests.unit.test_qt_control_grid_selection import Proc, app, on_processor_page, screen  # noqa: E402,F401


@pytest.fixture
def plugin_widget(monkeypatch):
    """Every processor has the spectrum widget (zynthian_widget_spectr30, a PluginView)"""
    from zynqt.screens import control
    monkeypatch.setattr(control.wd, "plugin_widget", lambda proc: "spectr30" if proc is not None else None)


def reload(cc, chain):
    """chain_manager.reload_processor on the chain's first processor: a new object, same id and
    place, the old one without chain"""
    old = chain.procs[0]
    new = Proc(old.get_name(), old.screens.items(), chain)
    new.id = old.id
    new.controllers_dict = old.controllers_dict
    chain.procs[0] = new
    old.chain = None
    cc.ui.set_current_processor(new)
    return old, new


def test_shown_again_after_a_reload_the_widget_has_the_new_processor(screen, plugin_widget):
    cc, chain, _ = screen
    on_processor_page(cc)
    assert cc.widgetType == "plugin" and cc.plugin_view.processor is chain.procs[0]
    cc.hide()                       # the processor options: Reload
    old, new = reload(cc, chain)
    cc.build()                      # chain control again
    assert cc.widgetType == "plugin"
    assert cc.plugin_view.processor is new


def test_reloaded_while_shown_the_widget_follows(screen, plugin_widget):
    cc, chain, _ = screen
    on_processor_page(cc)
    old, new = reload(cc, chain)
    cc.ui.bridge.chainsChanged.emit()
    # The view refreshes only while it is the page's widget: then on the new processor
    assert cc.widgetType != "plugin" or cc.plugin_view.processor is new
