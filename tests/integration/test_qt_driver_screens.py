"""Controller drivers in the Qt UI: what they take from zyngui.screens works with the Qt UI's
stand-ins (zynqt.tk_screens), and SS_GUI_SHOW_SCREEN reaches them with the Tk names."""

import threading
from types import SimpleNamespace

import pytest

pytest.importorskip("PySide6.QtCore")
tk_screens = pytest.importorskip("zynqt.tk_screens")

from tests.integration.test_ctrldev_drivers import IDEV_IN, IDEV_OUT, driver_env, load_class  # noqa: E402,F401

pytestmark = pytest.mark.integration


def qt_zyngui(current_screen):
    calls = []
    ui = SimpleNamespace(current_screen=current_screen, calls=calls,
                         _gui=SimpleNamespace(run=lambda fn: fn()),
                         launcher=SimpleNamespace(edit_pad=lambda: calls.append("edit_pad"),
                                                  padsChanged=SimpleNamespace(emit=lambda: calls.append("pads"))),
                         pattern_editor=SimpleNamespace(undo=lambda: calls.append("undo"),
                                                        redo=lambda: calls.append("redo"), cursor=[0, 60]))
    ui.screens = tk_screens.TkScreens(ui)
    ui.get_current_screen = lambda: ui.current_screen
    ui.show_screen = lambda name: calls.append(f"show {name}")
    ui.wsleds = None
    return ui


@pytest.fixture
def qt_ui(monkeypatch):
    from zyngui import zynthian_gui_config
    ui = qt_zyngui("mixer")
    monkeypatch.setattr(zynthian_gui_config, "zyngui", ui, raising=False)
    return ui


def test_apc40_mixer_launcher_toggle(driver_env, qt_ui, monkeypatch):
    state_manager, zynsigman = driver_env
    sent = []
    monkeypatch.setattr(state_manager, "send_cuia", lambda cuia, params=None: sent.append(cuia))
    driver = load_class("zynthian_ctrldev_akai_apc_40_mk2")(state_manager, IDEV_IN, IDEV_OUT)
    driver.toggle_mixer_launcher()
    qt_ui.current_screen = "launcher"
    driver.toggle_mixer_launcher()
    assert sent == ["SCREEN_LAUNCHER", "SCREEN_MIXER"]


def test_apc_key25_mk2_refreshes_the_launcher(driver_env, qt_ui):
    from zyngine.ctrldev import zynthian_ctrldev_akai_apc_key25_mk2 as mod
    handler = SimpleNamespace(_libseq=SimpleNamespace(updateSequenceInfo=lambda: None))
    # The pad matrix handler's _refresh_ui, on a stand-in (it needs the whole driver otherwise)
    cls = next(c for c in vars(mod).values() if isinstance(c, type) and "_refresh_ui" in vars(c))
    cls._refresh_ui(handler)
    assert qt_ui.calls == ["pads"]


def test_mpk249_learns_the_tk_screen_names(driver_env, qt_ui):
    """The signal as ZynUI.notify_screen sends it reaches a driver (queued handler: run here)"""
    state_manager, zynsigman = driver_env
    driver = load_class("zynthian_ctrldev_akai_mpk249")(state_manager, IDEV_IN, IDEV_OUT)
    driver.init()
    try:
        handlers = [cb for cb, queued in zynsigman.signal_register[zynsigman.S_GUI][zynsigman.SS_GUI_SHOW_SCREEN]
                    if getattr(cb, "__self__", None) is driver]
        assert handlers, "the driver doesn't listen to SS_GUI_SHOW_SCREEN"
        for name in ("pattern_editor", "launcher", "chain_control"):
            for cb in handlers:
                cb(screen=name)
            assert driver._current_screen == name
    finally:
        driver.end()
