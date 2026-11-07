"""Computer keyboard bindings (zynthian_main.cb_keybinding): keys -> CUIAs, from the key binding
configuration that webconf's "UI > Keyboard Binding" page edits (zyngui.zynthian_gui_keybinding,
<config dir>/keybinding.json, Tk's defaults without it).

The map is keyed by X11 keycode (evdev code + 8) and X11 modifier bits (shift 1, caps lock 2,
ctrl 4, alt 8, num lock 16, super 64, altgr 128): what QKeyEvent.nativeScanCode() and
nativeModifiers() give on Wayland and X11. As in the Tk UI, ZYNSWITCH / ZYNPOT bindings send
press and release ("i,P" / "i,R"; "...,T" toggles on each press), the others run on press, also
repeated while the key is held.
"""

import logging

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QWindow

from zyngui import zynthian_gui_keybinding

# Modifier bits of the binding map, for keys without native modifiers (other platforms)
_QT_MODIFIERS = ((Qt.ShiftModifier, 1), (Qt.ControlModifier, 4), (Qt.AltModifier, 8),
                 (Qt.MetaModifier, 64))


class KeyBindingFilter(QObject):

    def __init__(self, ui, parent=None):
        super().__init__(parent)
        self.ui = ui
        self.toggles = {}   # keycode -> state of a ",T" binding

    def eventFilter(self, obj, event):
        kind = event.type()
        if kind not in (QEvent.KeyPress, QEvent.KeyRelease):
            return False
        # The application filter sees a key event once per receiver (the window, then the item
        # it is passed on to): handle it at the window only
        if not isinstance(obj, QWindow):
            return False
        if self.ui.keyboardShown:
            return False    # typing into the on-screen keyboard's text field
        keycode = event.nativeScanCode()
        if not keycode:
            return False
        modifiers = event.nativeModifiers()
        if not modifiers:
            mods = event.modifiers()
            modifiers = sum(bit for flag, bit in _QT_MODIFIERS if mods & flag)
        cuia = zynthian_gui_keybinding.get_key_action(keycode, modifiers)
        if not cuia:
            return False
        press = kind == QEvent.KeyPress
        queue = self.ui.cuia_queue
        if cuia.lower().startswith("zyn"):
            # Switch / encoder emulation: press and release, no auto repeat
            if event.isAutoRepeat():
                return True
            if cuia.endswith(",T"):
                if press:
                    state = self.toggles[keycode] = not self.toggles.get(keycode, False)
                    queue.put_nowait(cuia[:-1] + ("P" if state else "R"))
            else:
                queue.put_nowait(cuia + (",P" if press else ",R"))
        elif press:
            queue.put_nowait(cuia)
        logging.debug(f"key {keycode} mod {modifiers} -> {cuia} ({'press' if press else 'release'})")
        return True


def load_bindings():
    zynthian_gui_keybinding.load()
