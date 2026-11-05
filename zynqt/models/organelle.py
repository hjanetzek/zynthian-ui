"""Organelle widget (zynthian_widget_organelle): Organelle Pure Data patches draw on a 128x64 OLED
through OSC. OrganelleView keeps the display list (zyngui.zynthian_organelle_data, shared with
the Tk widget) and sends the device's controls (AUX and FS buttons, encoder) to the patch;
OledDisplay (a QML item) paints the list.

OSC messages arrive in the engine's OSC thread: a queued signal hands them to the GUI thread,
where the display list changes."""

import threading

import pyliblo3 as liblo
from PySide6.QtCore import QObject, QRectF, Qt, Property, Signal, Slot
from PySide6.QtGui import QColor, QFont, QPen
from PySide6.QtQuick import QQuickPaintedItem

from zyngui import zynthian_gui_config
from zyngui.zynthian_organelle_data import OLED_HEIGHT, OLED_WIDTH, OledScene, menu_touch_sequence, parse_oled


class OrganelleView(QObject):
    changed = Signal()       # display list
    stateChanged = Signal()  # LED, options
    _osc = Signal(str, list)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.scene = OledScene()
        self.processor = None
        self.osc_target = None
        self.in_parameter_view = False
        self._led = False
        self._osc.connect(self._handle)

    def set_processor(self, processor):
        if self.processor is not processor:
            self.processor = processor
            processor.engine.osc_reset_child_handlers()
            processor.engine.osc_add_child_handler(self._osc_thread)
            processor.engine.osc_flush_unhandle_messages()
        self.osc_target = processor.engine.osc_target
        self.stateChanged.emit()

    # From the patch

    def _osc_thread(self, path, args):
        """OSC thread: claim the messages this widget handles, process them in the GUI thread"""
        if path.startswith("/oled/") or path in ("/led", "/enc_up", "/enc_down", "/enc_sel"):
            self._osc.emit(path, list(args))
            return True
        return False

    def _handle(self, path, args):
        if path.startswith("/oled/"):
            op = parse_oled(path, args)
            if op:
                if op["op"] == "clear":
                    self.in_parameter_view = False
                if self.scene.apply(op):
                    self.changed.emit()
        elif path == "/led":
            if args:
                self._led = bool(int(args[0]))
                self.stateChanged.emit()
        elif path in ("/enc_up", "/enc_down"):
            # As the Tk widget: in a parameter view the encoder goes back to the menu
            if args and args[0] == 1:
                if self.in_parameter_view:
                    self._return_to_menu(-1 if path == "/enc_up" else 1)
                else:
                    self.send(path, 1)
        elif path == "/enc_sel":
            if args and args[0] == 1:
                self.in_parameter_view = True
                self.send("/enc_sel", 1)

    def _return_to_menu(self, step):
        self.in_parameter_view = False
        n = len(self.scene.menu_lines) or 5
        self.scene.set_page(max(0, min(n - 1, self.scene.page + step)))
        self.changed.emit()

    # To the patch

    def send(self, path, value):
        if self.osc_target:
            liblo.send(self.osc_target, path, value)

    def _sequence(self, seq):
        for delay, path, value in seq:
            threading.Timer(delay / 1000, self.send, (path, value)).start()

    @Slot(str, bool)
    def button(self, path, pressed):
        """AUX (/aux) or FS (/fs) pressed or released"""
        self.send(path, 1 if pressed else 0)

    @Slot(int)
    def encoder(self, step):
        """Turn the encoder (one step up or down, a pulse as from the hardware)"""
        path = "/enc_down" if step > 0 else "/enc_up"
        self._sequence([(0, path, 1), (50, path, 0)])

    @Slot()
    def encoderPress(self):
        self._sequence([(0, "/enc_sel", 1), (100, "/enc_sel", 0)])

    @Slot(float)
    def touch(self, oled_y):
        """Touch on the OLED at row oled_y: select the menu line there; in a parameter view,
        go on (enc_down) as the Tk widget"""
        index = self.scene.menu_index(oled_y)
        if index is not None and not self.in_parameter_view:
            self._sequence(menu_touch_sequence(self.scene.page, index))
            self.scene.set_page(index)
            self.changed.emit()
        elif self.in_parameter_view:
            self._sequence([(0, "/enc_down", 1), (50, "/enc_down", 0)])

    # For QML

    @Property(bool, notify=stateChanged)
    def led(self):
        return self._led

    @Property(bool, notify=stateChanged)
    def fsButton(self):
        try:
            return bool(self.processor.engine.preset_config.get("organelle_fs_button", True))
        except Exception:
            return True

    @Property(bool, notify=stateChanged)
    def selector(self):
        try:
            return bool(self.processor.engine.preset_config.get("organelle_selector", True))
        except Exception:
            return True


class OledDisplay(QQuickPaintedItem):
    """Paints an OrganelleView's display list, scaled to the item (QML: OledDisplay { view: … })"""
    viewChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._view = None
        self.setAntialiasing(False)

    def getView(self):
        return self._view

    def setView(self, view):
        if view is self._view:
            return
        if self._view:
            self._view.changed.disconnect(self.update)
        self._view = view
        if view:
            view.changed.connect(self.update)
        self.viewChanged.emit()
        self.update()

    view = Property(QObject, getView, setView, notify=viewChanged)

    def paint(self, painter):
        scale = min(self.width() / OLED_WIDTH, self.height() / OLED_HEIGHT)
        painter.fillRect(QRectF(0, 0, self.width(), self.height()), QColor("#000000"))
        if not self._view or scale <= 0:
            return
        painter.save()
        painter.translate((self.width() - scale * OLED_WIDTH) / 2, (self.height() - scale * OLED_HEIGHT) / 2)
        painter.scale(scale, scale)
        scene = self._view.scene
        white, black = QColor("#ffffff"), QColor("#000000")
        hl_bg = QColor(zynthian_gui_config.color_ctrl_bg_on)
        hl_tx = QColor(zynthian_gui_config.color_ctrl_tx)
        if scene.inverted is not None:
            painter.fillRect(QRectF(0, scene.inverted - 1, OLED_WIDTH, 10), hl_bg)
        font = QFont("FreeMono")
        font.setStyleHint(QFont.Monospace)
        for item in scene.items:
            op = item["op"]
            color = white if item.get("color", 1) == 1 else black
            if op == "text":
                font.setPixelSize(max(4, round(0.95 * item["size"])))
                font.setBold(item["size"] > 16)
                painter.setFont(font)
                if item["x"] <= 10 and item["y"] == scene.inverted:
                    painter.setPen(hl_tx)
                else:
                    painter.setPen(color)
                painter.drawText(QRectF(item["x"], item["y"], OLED_WIDTH, item["size"] + 2),
                                 Qt.AlignLeft | Qt.AlignTop, item["text"])
            elif op == "pixel":
                painter.fillRect(QRectF(item["x"], item["y"], 1, 1), color)
            elif op == "line":
                painter.setPen(QPen(color, 1))
                painter.drawLine(item["x1"], item["y1"], item["x2"], item["y2"])
            elif op == "box":
                painter.setPen(QPen(color, 1))
                painter.setBrush(Qt.NoBrush)
                painter.drawRect(QRectF(item["x"] + 0.5, item["y"] + 0.5, item["w"] - 1, item["h"] - 1))
            elif op == "fill":
                painter.fillRect(QRectF(item["x"], item["y"], item["w"], item["h"]), color)
            elif op in ("circle", "fcircle"):
                painter.setPen(QPen(color, 1))
                painter.setBrush(color if op == "fcircle" else Qt.NoBrush)
                r = item["r"]
                painter.drawEllipse(QRectF(item["x"] - r, item["y"] - r, 2 * r, 2 * r))
            elif op == "invert_area":
                painter.fillRect(QRectF(item["x"], item["y"], item["w"], item["h"]), white)
        painter.restore()
