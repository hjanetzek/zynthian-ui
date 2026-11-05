"""Envelope and filter views for chain control pages (zynthian_widget_envelope, _filter): the
shape from the page's controllers, dragging changes them. Geometry and drag behaviour are
shared with the Tk widgets (zyngui.zynthian_widget_data); QML draws the polygons.

ChainControl sets the controller group and calls refresh() at its controller refresh rate."""

from PySide6.QtCore import QObject, QPointF, Property, Signal, Slot

from zyngui import zynthian_widget_data as wd

MARGIN = 10


def _points(coords):
    return [QPointF(coords[i], coords[i + 1]) for i in range(0, len(coords) - 1, 2)]


class EnvelopeView(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.zctrls = []
        self.fade_polarity = 1
        self._width = 400
        self._height = 200
        self._values = None
        self._shape = []
        self._drag_shape = []
        self._click_ranges = []
        self.drag_zctrl = None
        self.click_value = 0
        self.click_x = self.click_y = 0

    def set_group(self, group_zctrls):
        self.zctrls, self.fade_polarity = wd.envelope_zctrls(group_zctrls)
        self._values = None
        self.refresh()

    def _plot(self):
        return self._width - 2 * MARGIN, self._height - 2 * MARGIN

    def refresh(self):
        if not self.zctrls:
            return
        values = wd.envelope_values(self.zctrls)
        if values == self._values and not self.drag_zctrl:
            return
        self._values = values
        pw, ph = self._plot()
        coords, self._click_ranges, drag = wd.envelope_geometry(self.zctrls, values, self.fade_polarity, pw, ph,
                                                                MARGIN, MARGIN, self.drag_zctrl)
        self._shape = _points(coords)
        self._drag_shape = _points(drag) if drag else []
        self.changed.emit()

    @Slot(float, float)
    def setSize(self, width, height):
        self._width, self._height = max(40, width), max(40, height)
        self._values = None
        self.refresh()

    @Property("QVariantList", notify=changed)
    def shape(self):
        return self._shape

    @Property("QVariantList", notify=changed)
    def dragShape(self):
        return self._drag_shape

    @Slot(float, float)
    def press(self, x, y):
        self.drag_zctrl = wd.envelope_hit(self.zctrls, self._click_ranges, x)
        if self.drag_zctrl:
            self.click_value = self.drag_zctrl.value
            self.click_x, self.click_y = x, y
            self.refresh()

    @Slot(float, float)
    def drag(self, x, y):
        if self.drag_zctrl:
            pw, ph = self._plot()
            wd.envelope_drag(self.drag_zctrl, self.click_value, x - self.click_x, y - self.click_y,
                             len(self.zctrls), pw, ph, self.fade_polarity)
            self.refresh()

    @Slot()
    def release(self):
        self.drag_zctrl = None
        self._drag_shape = []
        self._values = None
        self.refresh()


class FilterView(QObject):
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.cutoff = None
        self.resonance = None
        self._width = 400
        self._height = 200
        self._values = None
        self._shape = []
        self.click = (0.5, 0.0)
        self.click_x = self.click_y = 0
        self.dragging = False

    def set_group(self, group_zctrls):
        self.cutoff, self.resonance = wd.filter_zctrls(group_zctrls)
        self._values = None
        self.refresh()

    def refresh(self):
        values = wd.filter_values(self.cutoff, self.resonance)
        if values == self._values:
            return
        self._values = values
        coords = wd.filter_curve(values[0], values[1], self._width, self._height, MARGIN, MARGIN, MARGIN, MARGIN)
        self._shape = _points(coords) if coords else []
        self.changed.emit()

    @Slot(float, float)
    def setSize(self, width, height):
        self._width, self._height = max(40, width), max(40, height)
        self._values = None
        self.refresh()

    @Property("QVariantList", notify=changed)
    def shape(self):
        return self._shape

    @Property("QVariantList", notify=changed)
    def gridY(self):
        """y of the dB grid lines"""
        gh = self._height - 2 * MARGIN
        return [wd.filter_db_y(db, MARGIN, gh) for db in wd.FILTER_DB_TICKS]

    @Slot(float, float)
    def press(self, x, y):
        self.click = wd.filter_values(self.cutoff, self.resonance)
        self.click_x, self.click_y = x, y
        self.dragging = True

    @Slot(float, float)
    def drag(self, x, y):
        if self.dragging:
            wd.filter_drag(self.cutoff, self.resonance, self.click[0], self.click[1],
                           (x - self.click_x) / self._width, (y - self.click_y) / self._height)
            self.refresh()

    @Slot()
    def release(self):
        self.dragging = False
