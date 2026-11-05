"""X-Y touchpad (zynthian_gui_control_xy): two controllers (state_manager.zctrl_x / zctrl_y, chosen
in a controller's options) on one touch surface. Positions are 0..1, y from the bottom (up is a
higher value; the Tk screen has the minimum at the top). Values changed elsewhere (MIDI, knobs)
move the cursor: a timer reads them while the screen is shown."""

from PySide6.QtCore import QObject, QTimer, Property, Signal, Slot

from zyngui.zynthian_control_xy_data import fraction_value, value_fraction


class ControlXY(QObject):
    name = "control_xy"

    changed = Signal()

    def __init__(self, ui, parent=None):
        super().__init__(parent)
        self.ui = ui
        self._last = None
        self._timer = QTimer(self, interval=50)
        self._timer.timeout.connect(self._poll)

    def _zctrls(self):
        sm = self.ui.state_manager
        return sm.zctrl_x, sm.zctrl_y

    def available(self):
        x, y = self._zctrls()
        return x is not None and y is not None

    # Screen (ZynUI)

    def build(self):
        self._last = None
        self._poll()
        self._timer.start()

    def hide(self):
        self._timer.stop()

    def back(self):
        return False

    def navigate(self, what):
        """Arrows nudge the controllers (as the Tk screen's encoders): left/right X, up/down Y"""
        x, y = self._zctrls()
        steps = {"left": (x, -1), "right": (x, 1), "up": (y, 1), "down": (y, -1)}
        if what in steps and steps[what][0] is not None:
            zctrl, step = steps[what]
            zctrl.nudge(step)
            self._poll()

    def _poll(self):
        x, y = self._zctrls()
        values = (x.value, y.value) if x is not None and y is not None else None
        if values != self._last:
            self._last = values
            self.changed.emit()

    # For QML

    @staticmethod
    def _text(zctrl):
        if zctrl is None:
            return ""
        try:
            label = zctrl.get_value2label()
        except Exception:
            label = zctrl.value
        if isinstance(label, float):
            label = f"{label:.3g}"
        return f"{zctrl.short_name or zctrl.name}: {label}"

    @Property(str, notify=changed)
    def xText(self):
        return self._text(self._zctrls()[0])

    @Property(str, notify=changed)
    def yText(self):
        return self._text(self._zctrls()[1])

    @Property(float, notify=changed)
    def fx(self):
        x = self._zctrls()[0]
        return value_fraction(x) if x is not None else 0.5

    @Property(float, notify=changed)
    def fy(self):
        y = self._zctrls()[1]
        return value_fraction(y) if y is not None else 0.5

    @Slot(float, float)
    def setPosition(self, fx, fy):
        """Touch at (fx, fy), both 0..1, fy from the bottom"""
        x, y = self._zctrls()
        if x is None or y is None:
            return
        vx = fraction_value(x, fx)
        if vx != x.value:
            x.set_value(vx, True)
        vy = fraction_value(y, fy)
        if vy != y.value:
            y.set_value(vy, True)
        self._poll()
