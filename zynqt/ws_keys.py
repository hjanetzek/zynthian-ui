"""Keys from websocket clients ({"key": "down"|"up", "code": KeyboardEvent.code}) as key events of
the Qt UI's window.

The Tk UI injects them into the X display with xdotool (zynthian_gui.websocket_key_event), where
they go through the key bindings like a real keyboard's. Here they are QKeyEvents sent to the QML
window with the native X11 keycode (evdev code + 8) and modifier bits, which the key bindings use
(zynqt.keyboard), and the Qt key and text, for QML's own handlers (the on-screen keyboard's text
field). Works the same on Wayland and X11.
"""

import logging

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QGuiApplication, QKeyEvent

# KeyboardEvent.code => (evdev code, Qt key, text, shifted text)
_KEYS = {
    "Escape": (1, Qt.Key_Escape, "", ""), "Minus": (12, Qt.Key_Minus, "-", "_"),
    "Equal": (13, Qt.Key_Equal, "=", "+"), "Backspace": (14, Qt.Key_Backspace, "", ""),
    "Tab": (15, Qt.Key_Tab, "", ""), "BracketLeft": (26, Qt.Key_BracketLeft, "[", "{"),
    "BracketRight": (27, Qt.Key_BracketRight, "]", "}"), "Enter": (28, Qt.Key_Return, "", ""),
    "ControlLeft": (29, Qt.Key_Control, "", ""), "Semicolon": (39, Qt.Key_Semicolon, ";", ":"),
    "Quote": (40, Qt.Key_Apostrophe, "'", '"'), "Backquote": (41, Qt.Key_QuoteLeft, "`", "~"),
    "ShiftLeft": (42, Qt.Key_Shift, "", ""), "Backslash": (43, Qt.Key_Backslash, "\\", "|"),
    "Comma": (51, Qt.Key_Comma, ",", "<"), "Period": (52, Qt.Key_Period, ".", ">"),
    "Slash": (53, Qt.Key_Slash, "/", "?"), "ShiftRight": (54, Qt.Key_Shift, "", ""),
    "AltLeft": (56, Qt.Key_Alt, "", ""), "Space": (57, Qt.Key_Space, " ", " "),
    "CapsLock": (58, Qt.Key_CapsLock, "", ""), "IntlBackslash": (86, Qt.Key_Less, "<", ">"),
    "NumpadEnter": (96, Qt.Key_Enter, "", ""), "ControlRight": (97, Qt.Key_Control, "", ""),
    "AltRight": (100, Qt.Key_AltGr, "", ""), "Home": (102, Qt.Key_Home, "", ""),
    "ArrowUp": (103, Qt.Key_Up, "", ""), "PageUp": (104, Qt.Key_PageUp, "", ""),
    "ArrowLeft": (105, Qt.Key_Left, "", ""), "ArrowRight": (106, Qt.Key_Right, "", ""),
    "End": (107, Qt.Key_End, "", ""), "ArrowDown": (108, Qt.Key_Down, "", ""),
    "PageDown": (109, Qt.Key_PageDown, "", ""), "Insert": (110, Qt.Key_Insert, "", ""),
    "Delete": (111, Qt.Key_Delete, "", ""), "MetaLeft": (125, Qt.Key_Meta, "", ""),
    "MetaRight": (126, Qt.Key_Meta, "", ""), "ContextMenu": (127, Qt.Key_Menu, "", ""),
}
_LETTER_ROWS = (("QWERTYUIOP", 16), ("ASDFGHJKL", 30), ("ZXCVBNM", 44))
for _row, _first in _LETTER_ROWS:
    for _i, _c in enumerate(_row):
        _KEYS["Key" + _c] = (_first + _i, getattr(Qt, "Key_" + _c), _c.lower(), _c)
_SHIFTED_DIGITS = ")!@#$%^&*("
for _d in range(10):
    _KEYS[f"Digit{_d}"] = (11 if _d == 0 else 1 + _d, getattr(Qt, f"Key_{_d}"), str(_d), _SHIFTED_DIGITS[_d])
_KEYPAD = {7: 71, 8: 72, 9: 73, 4: 75, 5: 76, 6: 77, 1: 79, 2: 80, 3: 81, 0: 82}
for _d, _code in _KEYPAD.items():
    _KEYS[f"Numpad{_d}"] = (_code, getattr(Qt, f"Key_{_d}"), str(_d), str(_d))
for _n in range(1, 25):
    _code = 58 + _n if _n <= 10 else 76 + _n if _n <= 12 else 170 + _n
    _KEYS[f"F{_n}"] = (_code, getattr(Qt, f"Key_F{_n}"), "", "")

# Modifier keys => (X11 modifier bit, Qt modifier)
_MODIFIERS = {
    "ShiftLeft": (1, Qt.ShiftModifier), "ShiftRight": (1, Qt.ShiftModifier),
    "ControlLeft": (4, Qt.ControlModifier), "ControlRight": (4, Qt.ControlModifier),
    "AltLeft": (8, Qt.AltModifier), "AltRight": (128, Qt.GroupSwitchModifier),
    "MetaLeft": (64, Qt.MetaModifier), "MetaRight": (64, Qt.MetaModifier),
}


def key_info(code):
    """(X11 keycode, Qt key, text, shifted text) of a KeyboardEvent.code, None if not supported"""
    k = _KEYS.get(code) if isinstance(code, str) else None
    if k is None:
        return None
    return (k[0] + 8,) + k[1:]


class WebsocketKeys:
    """Key events for the UI's window, with the modifiers the client holds (GUI thread)"""

    def __init__(self, ui):
        self.ui = ui
        self.held = set()   # modifier codes held down

    def modifiers(self):
        native, qt = 0, Qt.NoModifier
        for code in self.held:
            bit, mod = _MODIFIERS[code]
            native |= bit
            qt |= mod
        return native, qt

    def make_event(self, action, code):
        """The QKeyEvent for a client's key, None if not supported"""
        if action not in ("down", "up"):
            return None
        info = key_info(code)
        if info is None:
            logging.debug(f"Unsupported websocket key code '{code}'")
            return None
        keycode, key, text, shifted = info
        if code in _MODIFIERS:
            if action == "down":
                self.held.add(code)
            else:
                self.held.discard(code)
        native, qt = self.modifiers()
        if native & 4 or native & 8:
            text = ""   # shortcuts: no text
        elif native & 1:
            text = shifted
        kind = QEvent.KeyPress if action == "down" else QEvent.KeyRelease
        return QKeyEvent(kind, key, qt, keycode, 0, native, text)

    def event(self, action, code):
        ev = self.make_event(action, code)
        if ev is None:
            return
        frontend = getattr(self.ui, "frontend", None)
        window = None
        engine = getattr(frontend, "engine", None)
        if engine is not None and engine.rootObjects():
            window = engine.rootObjects()[0]
        if window is None:
            window = QGuiApplication.focusWindow()
        if window is None:
            logging.debug(f"websocket key '{code}': no window")
            return
        QGuiApplication.sendEvent(window, ev)
