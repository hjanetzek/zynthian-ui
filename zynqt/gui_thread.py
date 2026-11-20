"""Calls into the UI from any thread.

QObjects may only be used in the thread they live in, the GUI thread here. Code outside the Qt UI
calls the UI's entry points (show_info, show_screen, confirm, ...) from its own threads: engines,
MIDI (controller drivers), OSC, autoconnect, zynsigman's queue thread, tools/zyninject scripts that
start threads. A QTimer started from such a thread doesn't run (Qt warns "Timers cannot be started
from another thread"): an info box then stayed until the next screen change. A model reset from
another thread can crash QML.

GuiCaller.post() hands a callable to the GUI thread (a queued signal); @gui_thread makes a method
do that by itself when it is called from another thread. Such a call returns None at once and runs
later, in the order of the calls.
"""

import functools
import logging
import threading

from PySide6.QtCore import QObject, Qt, Signal, Slot


class GuiCaller(QObject):
    """Created in the GUI thread: post(fn) runs fn() there"""

    _call = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ident = threading.get_ident()
        self._call.connect(self._run, Qt.QueuedConnection)

    def in_gui_thread(self):
        return threading.get_ident() == self._ident

    def post(self, fn):
        self._call.emit(fn)

    def run(self, fn):
        """fn() now in the GUI thread, else posted there"""
        if self.in_gui_thread():
            return fn()
        self.post(fn)
        return None

    @Slot(object)
    def _run(self, fn):
        try:
            fn()
        except Exception as e:
            logging.exception(f"UI call from another thread failed: {e}")


def gui_thread(method):
    """Run method in the GUI thread: called from another thread, it is posted there (self._gui:
    the object's GuiCaller) and returns None"""
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        gui = self._gui
        if gui.in_gui_thread():
            return method(self, *args, **kwargs)
        logging.debug(f"{method.__name__}() from thread {threading.current_thread().name}: "
                      "posted to the GUI thread")
        gui.post(functools.partial(method, self, *args, **kwargs))
        return None
    return wrapper
