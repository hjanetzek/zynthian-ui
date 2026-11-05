"""Waveform view of an audio file processor (zynthian_widget_audio_file): audio player, clippy,
samplv1. The engine's view parameters, loading and the peaks are shared with the Tk widget
(zyngui.zynthian_audio_file_data); QML draws the peaks as filled shapes (one per channel), the
crop/loop markers, beat or cue markers and the play cursor.

Runs while shown (ChainControl shows it for the current page's processor)."""

import logging
from math import modf
from os.path import basename
from threading import Thread

from PySide6.QtCore import QObject, QPointF, QTimer, Property, Signal, Slot

from zyngui import zynthian_audio_file_data as afd


def format_time(time):
    return f"{int(time / 60):02d}:{int(time % 60):02d}.{int(modf(time)[0] * 1000):03}"


class AudioFileView(QObject):
    waveChanged = Signal()       # peaks (file, zoom, offset, size)
    markersChanged = Signal()
    cursorChanged = Signal()
    infoChanged = Signal()
    _loaded = Signal()           # from the loading thread

    def __init__(self, ui, parent=None):
        super().__init__(parent)
        self.ui = ui
        self.processor = None
        self.eng_type = afd.ENG_NONE
        self.zctrl = None
        self.clip_info = None
        self.fpath = None
        self.wave_data = None
        self.channels = 0
        self.frames = 0
        self.samplerate = None
        self.loading = False
        self.load_error = ""
        self.zoom = 1
        self.vzoom = 1.0
        self.offset = 0
        self.crop_start = 0
        self.crop_end = 0
        self.loop_markers = False
        self.loop_start = 0
        self.loop_end = 0
        self.beats = 0
        self.cursor_pos = None
        self._width = 600
        self._height = 200
        self._paths = []
        self._markers = {}
        self._cursor_x = -1.0
        self._info = ""
        self._timer = QTimer(self, interval=50)
        self._timer.timeout.connect(self._refresh)
        self._loaded.connect(self._on_loaded)

    # Shown for a processor (ChainControl)

    def set_processor(self, processor):
        if processor is self.processor:
            return
        self.processor = processor
        self.eng_type = afd.engine_type(processor)
        self.zctrl = afd.file_zctrl(processor) if processor else None
        self.clip_info = None
        if self.eng_type == afd.ENG_CLIPPY and self.zctrl:
            self.clip_info = afd.clippy_info(processor, self.zctrl, self.ui.state_manager.zynseq)
        elif self.eng_type in (afd.ENG_GLOBAL_AP, afd.ENG_CHAIN_AP):
            processor.engine.set_monitored_processor(processor)
        self.fpath = None
        self.wave_data = None
        self.frames = 0
        self._paths = []
        self.waveChanged.emit()

    def start(self):
        self._timer.start()

    def stop(self):
        self._timer.stop()

    @Slot(float, float)
    def setSize(self, width, height):
        if int(width) != self._width or int(height) != self._height:
            self._width = max(1, int(width))
            self._height = max(1, int(height))
            self._redraw_wave()

    # Refresh (as zynthian_widget_audio_file.refresh_gui)

    def _file_path(self):
        if self.zctrl:
            return self.zctrl.value
        try:
            return self.processor.engine.get_monitors_dict().get("filename")
        except Exception:
            return None

    def _refresh(self):
        if self.processor is None or self.loading:
            return
        fpath = self._file_path()
        if not fpath or fpath == "_":
            if self.fpath:
                self.fpath = None
                self.wave_data = None
                self.frames = 0
                self._paths = []
                self._set_info("No file")
                self.waveChanged.emit()
            return
        if fpath != self.fpath:
            self.fpath = fpath
            self._load(fpath)
            return
        try:
            monitors = self.processor.engine.get_monitors_dict()
        except Exception:
            monitors = {}
        v = afd.engine_view(self.eng_type, self.processor, monitors, self.ui.state_manager.zynseq, self.samplerate,
                            self.frames, self.zoom, self.crop_start, self.crop_end, self.clip_info, self.zctrl)
        redraw = markers = False
        for key in ("zoom", "offset", "vzoom"):
            if v[key] is not None and v[key] != getattr(self, key):
                setattr(self, key, v[key])
                redraw = True
        for key in ("crop_start", "crop_end", "loop_markers", "loop_start", "loop_end", "beats"):
            if v[key] is not None and v[key] != getattr(self, key):
                setattr(self, key, v[key])
                markers = True
        if v["update_cue"]:
            markers = True
        if redraw:
            self._redraw_wave()
        elif markers:
            self._update_markers()
        if v["cursor_pos"] != self.cursor_pos or redraw:
            self.cursor_pos = v["cursor_pos"]
            self._update_cursor()
            self._update_info(monitors)

    # Loading in the background (large files)

    def _load(self, fpath):
        self.loading = True
        self._set_info("Loading waveform ...")

        def load():
            try:
                self.wave_data, self.channels, self.frames, self.samplerate = afd.load_wave(fpath)
                self.load_error = ""
            except MemoryError:
                self.wave_data, self.frames, self.load_error = None, 0, "File too large!"
            except Exception as e:
                logging.warning(f"Can't display waveform: {e}")
                self.wave_data, self.frames, self.load_error = None, 0, "Display error!"
            self._loaded.emit()

        Thread(target=load, name="load_waveform", daemon=True).start()

    def _on_loaded(self):
        if self.clip_info and self.frames:
            try:
                for key, value in afd.clippy_values(self.processor, self.clip_info).items():
                    if key in ("zoom", "crop_start", "crop_end", "beats"):
                        setattr(self, key, value)
            except Exception as e:
                logging.error(f"Can't get clip audio values for clip {self.clip_info} => {e}")
        else:
            self.crop_start = 0
            self.crop_end = self.frames
        self.offset = 0
        self.loading = False
        self._redraw_wave()
        self._set_info(self.load_error or basename(self.fpath or ""))

    # Drawing data for QML

    def _length(self):
        return max(1, self.frames // max(1, self.zoom))

    def _redraw_wave(self):
        if self.wave_data is None or not self.frames:
            self._paths = []
            self.waveChanged.emit()
            return
        length = self._length()
        self.offset = max(0, min(self.offset, self.frames - length))
        mins, maxs = afd.peaks(self.wave_data, self.offset, length, self._width)
        ch_h = self._height / max(1, self.channels)
        amp = self.vzoom * ch_h / 2
        paths = []
        for ch in range(self.channels):
            # Outline: the maxima left to right, the minima back (numpy, then one list each)
            y0 = ch_h * (ch + 0.5)
            ytop = (y0 - (maxs[ch] * amp).clip(max=ch_h / 2)).tolist()
            ybottom = (y0 - (mins[ch] * amp).clip(min=-ch_h / 2)).tolist()
            n = len(ytop)
            top = [QPointF(x, y) for x, y in enumerate(ytop)]
            bottom = [QPointF(x, ybottom[x]) for x in range(n - 1, -1, -1)]
            paths.append(top + bottom + top[:1])
        self._paths = paths
        self.waveChanged.emit()
        self._update_markers()
        self._update_cursor()

    def _x(self, frame):
        return self._width / self.frames * self.zoom * (frame - self.offset) if self.frames else -1.0

    def _update_markers(self):
        m = {"cropStart": self._x(self.crop_start), "cropEnd": self._x(self.crop_end),
             "loopStart": self._x(self.loop_start) if self.loop_markers else -1.0,
             "loopEnd": self._x(self.loop_end) if self.loop_markers else -1.0, "beats": []}
        if self.frames:
            x1, x2 = m["cropStart"], m["cropEnd"]
            if self.beats > 0:
                bpb = self.ui.state_manager.zynseq.bpb or 4
                dx = (x2 - x1) / self.beats
                if dx > 4:
                    n = self.beats if dx >= 16 else max(1, self.beats // bpb)
                    for i in range(1, n):
                        m["beats"].append({"x": x1 + i * (x2 - x1) / n, "strong": dx < 16 or i % bpb == 0})
            elif self.eng_type in (afd.ENG_GLOBAL_AP, afd.ENG_CHAIN_AP) and self.samplerate:
                selected = self.processor.controllers_dict['cue'].value
                for cue, cue_val in enumerate(self.processor.cues):
                    m["beats"].append({"x": self._x(self.samplerate * cue_val), "strong": cue == selected})
        self._markers = m
        self.markersChanged.emit()

    def _update_cursor(self):
        if self.cursor_pos is None or not self.frames:
            x = -1.0
        else:
            x = self._x(self.crop_start + self.cursor_pos * (self.crop_end - self.crop_start))
        if x != self._cursor_x:
            self._cursor_x = x
            self.cursorChanged.emit()

    def _update_info(self, monitors):
        if not self.samplerate or not self.fpath:
            return
        dur = self.crop_end - self.crop_start
        speed = monitors.get("speed", 1) or 1
        dur /= speed
        match monitors.get("info", 0):
            case 1:
                time = format_time((self.cursor_pos or 0) * dur * speed / self.samplerate)
            case 2:
                time = format_time((1.0 - (self.cursor_pos or 0)) * dur / self.samplerate)
            case 3:
                time = self.samplerate
            case 4:
                time = monitors.get("codec", "")
            case _:
                time = format_time(dur / self.samplerate)
        self._set_info(f"{basename(self.fpath)} [{time}]")

    def _set_info(self, text):
        if text != self._info:
            self._info = text
            self.infoChanged.emit()

    # For QML

    @Property("QVariantList", notify=waveChanged)
    def paths(self):
        return self._paths

    @Property("QVariantMap", notify=markersChanged)
    def markers(self):
        return self._markers

    @Property(float, notify=cursorChanged)
    def cursorX(self):
        return self._cursor_x

    @Property(str, notify=infoChanged)
    def info(self):
        return self._info

    @Slot(int)
    def nudgeZoom(self, step):
        try:
            self.processor.controllers_dict['zoom'].nudge(step)
        except Exception:
            pass
