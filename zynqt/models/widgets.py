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


class PluginView(QObject):
    """Plugin widgets (zynthian_widget_spectr30, tunaone, GxGraphicEQ, nam, aidax,
    chord_analyzer): what they show from the engine's monitors and controllers, as a dict for
    QML, by kind:

    bars (spectrum, graphic EQ): labels, bars [[bottom, top, tick], ...] as height fractions,
        zero (0 dB line or -1), editable (EQ: drag sets the band's gain);
    tuner: note, cents (-50..50), color, or note "" without signal;
    text: lines (title, text) pairs (NAM model, chord analyzer);
    aidax: meters (in, out levels 0..1) and lines;
    tempo: big (BPM text), tap on it taps the tempo;
    radio: lines (title, info, bitrate, codec / channels) and artwork (image path).
    """
    changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.processor = None
        self.name = None
        self._data = {}
        self.levels = [0.0, 0.0]

    def set_processor(self, processor, name):
        self.processor = processor
        self.name = name
        self.levels = [0.0, 0.0]
        self._data = {}
        self.refresh()

    def refresh(self):
        proc = self.processor
        if proc is None:
            return
        try:
            monitors = proc.engine.get_monitors_dict() or {}
        except Exception:
            monitors = {}
        data = {"kind": "", "labels": [], "bars": [], "zero": -1, "editable": False}
        match self.name:
            case "spectr30":
                data.update(kind="bars", labels=wd.SPECTRUM_LABELS,
                            bars=[[0.0, bar, tick] for bar, tick in wd.spectrum_levels(proc, monitors)])
            case "GxGraphicEQ":
                bands = wd.gx_eq_bands(proc)
                if bands:
                    data.update(kind="bars", labels=bands[1], zero=wd.GX_ZERO, editable=True,
                                bars=[list(b) for b in wd.gx_eq_levels(proc, monitors, len(bands[0]))])
            case "tunaone":
                state = wd.tuner_state(monitors)
                data.update(kind="tuner", note=state[0] if state else "", cents=state[1] if state else 0,
                            color=state[2] if state else "#808080")
            case "nam":
                data.update(kind="text", lines=[["Model", self._file(proc, "model")]])
            case "chord_analyzer":
                texts = wd.chord_texts(monitors)
                old = self._data.get("lines") if self._data.get("kind") == "text" else None
                data.update(kind="text", lines=[["Chord", texts[0]], ["", texts[1]]] if texts else
                            (old or [["Chord", "-"], ["", ""]]))
            case "aidax":
                for i, key in enumerate(("MeterIn", "MeterOut")):
                    if key in monitors:
                        self.levels[i] = wd.meter_fall(self.levels[i], monitors[key])
                data.update(kind="aidax", meters=[min(1.0, v) for v in self.levels],
                            lines=[["Model", self._file(proc, "json")], ["Cabinet", self._file(proc, "cabinet")]])
            case "tempo":
                try:
                    tempo = self.processor.engine.state_manager.zynseq.get_tempo()
                except Exception:
                    tempo = 0
                data.update(kind="tempo", big=f"{tempo:.1f} BPM")
            case "inet_radio":
                m = monitors
                data.update(kind="radio", artwork=m.get("artwork") or "",
                            lines=[["", m.get("title") or ""], ["", m.get("info") or ""],
                                   ["", " ".join(str(m.get(k) or "") for k in ("bitrate", "codec", "channels")).strip()]])
        if data != self._data:
            self._data = data
            self.changed.emit()

    @staticmethod
    def _file(proc, symbol):
        try:
            return str(proc.controllers_dict[symbol].value).rsplit("/", 1)[-1]
        except Exception:
            return ""

    @Property("QVariantMap", notify=changed)
    def data(self):
        return self._data

    @Slot()
    def tap(self):
        """Tempo widget: tap tempo"""
        if self.name == "tempo":
            try:
                self.processor.engine.state_manager.zynseq.tap_tempo()
            except Exception:
                pass

    @Slot(int, float)
    def dragBand(self, band, height_fraction):
        """Graphic EQ: set band's gain from a touch (0 bottom .. 1 top)"""
        if self.name == "GxGraphicEQ" and self.processor:
            wd.gx_eq_drag(self.processor, band, max(0.0, min(1.0, height_fraction)))
            self.refresh()


class EuclidSeqView(QObject):
    """Euclidean sequencer widget (zynthian_widget_euclidseq, EuclidSeq6 Pure Data patch): the
    shared model (zyngui.zynthian_euclidseq_data) keeps the state from the patch's OSC messages
    and sends the notes on each trigger; this gives QML the six channels' points and the
    selected channel's values. Model changes come from the engine's OSC thread too: a queued
    signal brings them to the GUI thread."""
    changed = Signal()
    _modelChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        from zyngui.zynthian_euclidseq_data import EuclidSeqModel
        self.model = EuclidSeqModel(on_change=self._modelChanged.emit)
        self._modelChanged.connect(self._update)
        self._channels = []
        self._panel = {}
        self._update()

    def set_processor(self, processor):
        self.model.set_processor(processor)
        self._update()

    def _update(self):
        m = self.model
        channels = []
        for k in range(m.channels):
            pos = m.play_position(k)
            channels.append({"dots": [[x, y] for x, y in m.step_dots(k)],
                             "hits": [[x, y] for x, y in m.hit_points(k)],
                             "play": [pos[0], pos[1], bool(pos[2])] if pos else [],
                             "note": m.note_numbers[k], "selected": k == m.select_ch, "muted": m.mute[k]})
        ch = m.select_ch
        self._channels = channels
        self._panel = {"mode": m.display_mode.capitalize(), "channel": ch + 1, "length": m.limit[ch],
                       "hits": m.hits[ch], "offset": m.offset[ch], "interval": m.interval_value[ch],
                       "showInterval": m.display_mode == "interval", "mute": m.mute[ch]}
        self.changed.emit()

    @Property("QVariantList", notify=changed)
    def channels(self):
        return self._channels

    @Property("QVariantMap", notify=changed)
    def panel(self):
        return self._panel

    @Slot(int)
    def selectChannel(self, ch):
        self.model.select_channel(ch)

    @Slot(int, int)
    def nudgeNote(self, ch, step):
        self.model.nudge_note(ch, step)

    @Slot(str, int)
    def adjust(self, key, step):
        self.model.adjust_param(key, step)

    @Slot()
    def toggleMute(self):
        self.model.toggle_mute()
