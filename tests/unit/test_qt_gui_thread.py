"""The Qt UI from other threads (zynqt.gui_thread): show_info() and other entry points called
outside the GUI thread run in the GUI thread; the info box is cleared after its time (the QTimer
didn't run when started from another thread)."""

import threading
import time

import pytest

QtCore = pytest.importorskip("PySide6.QtCore")
ui_mod = pytest.importorskip("zynqt.ui")

from zynqt.gui_thread import GuiCaller, gui_thread  # noqa: E402

ZynUI = ui_mod.ZynUI


@pytest.fixture(scope="module")
def app():
    return QtCore.QCoreApplication.instance() or QtCore.QCoreApplication([])


def wait_for(app, cond, timeout=3.0):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        app.processEvents(QtCore.QEventLoop.AllEvents, 20)
        if cond():
            return True
        time.sleep(0.005)
    return cond()


def in_thread(fn):
    t = threading.Thread(target=fn, name="worker")
    t.start()
    t.join()


class InfoUI(QtCore.QObject):
    """ZynUI's info box: its methods on a light QObject (ZynUI itself starts zynthian)"""
    infoChanged = QtCore.Signal()
    show_info = ZynUI.show_info
    _set_info = ZynUI._set_info

    def __init__(self):
        super().__init__()
        self._gui = GuiCaller(self)
        self._info = ""
        self._info_timer = QtCore.QTimer(self, singleShot=True, interval=2500)
        self._info_timer.timeout.connect(lambda: self._set_info(""))


def test_show_info_from_a_worker_thread_is_cleared(app):
    ui = InfoUI()
    in_thread(lambda: ui.show_info("'control' is not in the Qt UI yet.", 100))
    assert wait_for(app, lambda: ui._info != ""), "the message never came"
    assert ui._info_timer.isActive()
    assert wait_for(app, lambda: ui._info == "", timeout=2.0), "the info box stayed"


def test_show_info_in_the_gui_thread_runs_at_once(app):
    ui = InfoUI()
    ui.show_info("now", 50)
    assert ui._info == "now"
    assert wait_for(app, lambda: ui._info == "")


def test_gui_thread_calls_keep_their_order_and_thread(app):
    class Obj(QtCore.QObject):
        def __init__(self):
            super().__init__()
            self._gui = GuiCaller(self)
            self.calls = []

        @gui_thread
        def f(self, x):
            self.calls.append((x, threading.get_ident()))
            return x

    o = Obj()
    assert o.f(0) == 0
    results = []
    in_thread(lambda: results.extend([o.f(1), o.f(2)]))
    assert results == [None, None]   # posted
    assert wait_for(app, lambda: len(o.calls) == 3)
    main = threading.get_ident()
    assert o.calls == [(0, main), (1, main), (2, main)]
