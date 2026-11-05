#!/usr/bin/env python3
"""M0 spike for the Qt Quick port (docs/qt-port-plan.md): a mock mixer, a long list and the V5
touch keypad, without zynthian's backend. Measures what the Duet does with PySide6 + Qt Quick.

    python3 zynqt/spike/spike.py [--fullscreen] [--bench SECONDS] [--meter-hz HZ] [--no-switch]

--bench: switch between the screens every second and log, per switch, the time from the switch
to the next frame on screen; every 5 s the frame rate and the Python time spent per meter update.
--meter-hz: meter update rate (default 60, 0: no meter updates); --no-switch: stay on the mixer.
The output goes to stdout. Meter levels come from Python at 60 Hz, as zynmixer's DPM data would.
"""

import argparse
import math
import os
import random
import sys
import time

from PySide6.QtCore import (QAbstractListModel, QModelIndex, QObject, QTimer, Qt, Property, Signal,
                            Slot, QUrl)
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

NUM_STRIPS = 16
LIST_ITEMS = 200
METER_HZ = 60


class Meters(QObject):
    """Levels (0..1) of all strips, two channels each, updated in one go like zynmixer's
    update_dpm_states(): QML binds each meter to one entry."""

    levelsChanged = Signal()

    def __init__(self, count, hz=METER_HZ):
        super().__init__()
        self._levels = [0.0] * (2 * count)
        self._phase = [random.random() * math.tau for _ in range(2 * count)]
        self._t0 = time.monotonic()
        self.update_seconds = 0.0
        self.emit_seconds = 0.0
        self.updates = 0
        self._timer = QTimer(self, interval=round(1000 / hz) if hz else 1000, timerType=Qt.PreciseTimer)
        self._timer.timeout.connect(self._update)
        if hz:
            self._timer.start()

    @Property("QVariantList", notify=levelsChanged)
    def levels(self):
        return self._levels

    def _update(self):
        t0 = time.perf_counter()
        t = time.monotonic() - self._t0
        self._levels = [max(0.0, min(1.0, 0.55 + 0.4 * math.sin(1.7 * t + p) * math.sin(0.3 * t + 2 * p)
                                     + random.uniform(-0.05, 0.05))) for p in self._phase]
        t1 = time.perf_counter()
        self.levelsChanged.emit()
        self.update_seconds += time.perf_counter() - t0
        self.emit_seconds += time.perf_counter() - t1
        self.updates += 1


class StripModel(QAbstractListModel):
    NameRole, LevelRole, MuteRole, SoloRole = range(Qt.UserRole + 1, Qt.UserRole + 5)

    def __init__(self, count):
        super().__init__()
        self._strips = [{"name": f"Chain {i + 1}", "level": 0.75, "mute": False, "solo": False}
                        for i in range(count)]

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._strips)

    def roleNames(self):
        return {self.NameRole: b"name", self.LevelRole: b"level", self.MuteRole: b"mute",
                self.SoloRole: b"solo"}

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        key = self.roleNames().get(role)
        return self._strips[index.row()][key.decode()] if key else None

    def _set(self, row, key, role, value):
        if self._strips[row][key] != value:
            self._strips[row][key] = value
            i = self.index(row)
            self.dataChanged.emit(i, i, [role])

    @Slot(int, float)
    def setLevel(self, row, value):
        self._set(row, "level", self.LevelRole, max(0.0, min(1.0, value)))

    @Slot(int)
    def toggleMute(self, row):
        self._set(row, "mute", self.MuteRole, not self._strips[row]["mute"])

    @Slot(int)
    def toggleSolo(self, row):
        self._set(row, "solo", self.SoloRole, not self._strips[row]["solo"])


class ListModel(QAbstractListModel):
    TitleRole, InfoRole, SeparatorRole = range(Qt.UserRole + 1, Qt.UserRole + 4)

    def __init__(self, count):
        super().__init__()
        self._items = []
        for i in range(count):
            if i % 25 == 0:
                self._items.append((f"> SECTION {i // 25 + 1}", "", True))
            else:
                self._items.append((f"Preset {i:03d}",
                                    f"Preset {i:03d}: a description that is long enough to wrap "
                                    f"over a few lines in the info pane, as engine and preset "
                                    f"descriptions do.", False))

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._items)

    def roleNames(self):
        return {self.TitleRole: b"title", self.InfoRole: b"info", self.SeparatorRole: b"separator"}

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        title, info, separator = self._items[index.row()]
        return {self.TitleRole: title, self.InfoRole: info, self.SeparatorRole: separator}.get(role)


class Bench(QObject):
    """Switches screens and measures the time until the next frame is on screen."""

    screenRequested = Signal(int)

    def __init__(self, window, meters, seconds, switch=True):
        super().__init__()
        self._window = window
        self._meters = meters
        self._end = time.monotonic() + seconds
        self._frames = 0
        self._switch_t0 = None
        self._screen = 0
        self._last_report = time.monotonic()
        self._switch_times = []
        window.frameSwapped.connect(self._frame_swapped, Qt.DirectConnection)
        self._switch_timer = QTimer(self, interval=1000)
        self._switch_timer.timeout.connect(self._switch)
        self._switch_timer.start()
        self._do_switch = switch
        self._report_timer = QTimer(self, interval=5000)
        self._report_timer.timeout.connect(self._report)
        self._report_timer.start()

    def _frame_swapped(self):
        # Render thread (threaded render loop): keep it to counting and one timestamp
        self._frames += 1
        if self._switch_t0 is not None:
            self._switch_times.append(time.perf_counter() - self._switch_t0)
            self._switch_t0 = None

    def _switch(self):
        if time.monotonic() > self._end:
            self._report()
            QGuiApplication.quit()
            return
        if not self._do_switch:
            return
        self._screen = (self._screen + 1) % 2
        self._switch_t0 = time.perf_counter()
        self.screenRequested.emit(self._screen)

    def _report(self):
        now = time.monotonic()
        dt = now - self._last_report
        self._last_report = now
        m = self._meters
        per_update = 1000 * m.update_seconds / m.updates if m.updates else 0
        per_emit = 1000 * m.emit_seconds / m.updates if m.updates else 0
        switches = " ".join(f"{1000 * s:.0f}" for s in self._switch_times)
        print(f"fps {self._frames / dt:5.1f}  meter update {per_update:.2f} ms (Python), "
              f"of which QML bindings {per_emit:.2f} ms  "
              f"switch to frame [ms]: {switches}", flush=True)
        self._frames = 0
        self._switch_times = []
        m.update_seconds = 0.0
        m.emit_seconds = 0.0
        m.updates = 0


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--fullscreen", action="store_true")
    parser.add_argument("--bench", type=float, metavar="SECONDS")
    parser.add_argument("--meter-hz", type=float, default=METER_HZ)
    parser.add_argument("--no-switch", action="store_true")
    args = parser.parse_args()

    t_start = time.perf_counter()
    app = QGuiApplication(sys.argv)
    meters = Meters(NUM_STRIPS, args.meter_hz)
    strips = StripModel(NUM_STRIPS)
    items = ListModel(LIST_ITEMS)

    engine = QQmlApplicationEngine()
    ctx = engine.rootContext()
    ctx.setContextProperty("meters", meters)
    ctx.setContextProperty("strips", strips)
    ctx.setContextProperty("listItems", items)
    ctx.setContextProperty("startFullScreen", args.fullscreen)
    engine.load(QUrl.fromLocalFile(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                "qml", "Main.qml")))
    if not engine.rootObjects():
        return 1
    window = engine.rootObjects()[0]

    def first_frame():
        print(f"first frame after {1000 * (time.perf_counter() - t_start):.0f} ms", flush=True)
        window.frameSwapped.disconnect(first_frame)
    window.frameSwapped.connect(first_frame)

    if args.bench:
        bench = Bench(window, meters, args.bench, switch=not args.no_switch)
        bench.screenRequested.connect(lambda i: window.setProperty("currentScreen", i))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
